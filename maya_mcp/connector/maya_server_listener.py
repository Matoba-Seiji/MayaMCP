#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Maya 内部 Socket Server 监听脚本。

此脚本需要在 Maya 内部运行（通过 Script Editor 执行，或 userSetup 自动加载）。

启动后在后台线程监听 TCP 端口（默认 50011），接收来自 MCP Server 的 Python 脚本，
通过 maya.utils.executeInMainThreadWithResult 调度到 **主线程** 执行（保证 maya.cmds 可用），
执行完成后将结果返回。

通信协议:
    请求: [4字节大端序uint32: 消息体长度] + [UTF-8编码的Python脚本]
    响应: [4字节大端序uint32: 消息体长度] + [UTF-8编码的结果字符串]

用法（在 Maya Script Editor 的 Python 标签中执行）:
    import maya_server_listener        # 若已加入 sys.path
    或直接 exec 本文件内容。

停止:
    stop_mcp_server()
"""

import socket
import struct
import threading
import traceback
import json

import maya.utils

# ============================================================
# 配置
# ============================================================
HOST = '127.0.0.1'
PORT = 50011
HEADER_SIZE = 4
RECV_BUFSIZE = 4096

# ============================================================
# 全局变量
# ============================================================
_server_running = False
_server_thread = None
_server_socket = None

# 跨请求保持变量状态的执行上下文
_exec_globals = {}


# ============================================================
# 通信协议
# ============================================================
def _recv_all(conn):
    header_data = b''
    while len(header_data) < HEADER_SIZE:
        chunk = conn.recv(HEADER_SIZE - len(header_data))
        if not chunk:
            raise ConnectionError("客户端连接已关闭")
        header_data += chunk

    msg_length = struct.unpack('>I', header_data)[0]
    if msg_length == 0:
        return ''

    body_data = b''
    while len(body_data) < msg_length:
        remaining = msg_length - len(body_data)
        chunk = conn.recv(min(remaining, RECV_BUFSIZE))
        if not chunk:
            raise ConnectionError("客户端连接已关闭，消息体不完整")
        body_data += chunk

    return body_data.decode('utf-8')


def _pack_message(data):
    encoded = data.encode('utf-8')
    header = struct.pack('>I', len(encoded))
    return header + encoded


# ============================================================
# 脚本执行 (在主线程中由 executeInMainThreadWithResult 调用)
# ============================================================
def _execute_python(script):
    """在 Maya 主线程的 Python 环境中执行脚本并返回结果字符串。

    脚本中如果设置了 _mcp_maya_results 变量，则以该变量值作为返回结果。
    """
    global _exec_globals
    try:
        _exec_globals.pop('_mcp_maya_results', None)
        exec(script, _exec_globals)

        try:
            import maya.cmds as cmds
            cmds.refresh()
        except Exception:
            pass

        result = _exec_globals.get('_mcp_maya_results', None)
        if result is None:
            return ''
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(result)
    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            'success': False,
            'message': f'Maya 执行脚本出错: {str(e)}',
            'traceback': traceback.format_exc()
        }, ensure_ascii=False)


# ============================================================
# 后台线程: Socket Server
# ============================================================
def _handle_client(conn, addr):
    try:
        print(f"[MayaMCP] 客户端已连接: {addr}")
        script = _recv_all(conn)
        if not script:
            print("[MayaMCP] 收到空脚本，跳过")
            conn.sendall(_pack_message(''))
            return

        print(f"[MayaMCP] 收到脚本 ({len(script)} 字符)，调度到主线程执行...")
        # 调度到 Maya 主线程执行并阻塞等待结果
        result = maya.utils.executeInMainThreadWithResult(_execute_python, script)
        if result is None:
            result = ''

        conn.sendall(_pack_message(result))
        print(f"[MayaMCP] 结果已发送 ({len(result)} 字符)")

    except ConnectionError as e:
        print(f"[MayaMCP] 连接错误: {e}")
    except Exception as e:
        print(f"[MayaMCP] 处理请求出错: {e}")
        traceback.print_exc()
        try:
            error_msg = json.dumps({'success': False, 'message': f'服务端处理出错: {str(e)}'}, ensure_ascii=False)
            conn.sendall(_pack_message(error_msg))
        except Exception:
            pass
    finally:
        conn.close()


def _server_loop():
    global _server_running, _server_socket

    _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _server_socket.settimeout(1.0)

    try:
        _server_socket.bind((HOST, PORT))
        _server_socket.listen(5)
        print(f"[MayaMCP] Socket Server 已启动，监听 {HOST}:{PORT}")
        print("[MayaMCP] 等待 MCP Server 连接...")

        while _server_running:
            try:
                conn, addr = _server_socket.accept()
                t = threading.Thread(target=_handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break
    except Exception as e:
        print(f"[MayaMCP] 服务器错误: {e}")
        traceback.print_exc()
    finally:
        if _server_socket:
            _server_socket.close()
            _server_socket = None
        print("[MayaMCP] Socket Server 已停止")


# ============================================================
# 公共 API
# ============================================================
def start_mcp_server(host=HOST, port=PORT):
    """启动 MCP Socket Server。"""
    global _server_running, _server_thread, HOST, PORT

    if _server_running:
        print("[MayaMCP] 服务器已在运行中")
        return

    HOST = host
    PORT = port
    _server_running = True
    _server_thread = threading.Thread(target=_server_loop, daemon=True)
    _server_thread.start()
    print(f"[MayaMCP] 服务器启动中... (host={host}, port={port})")


def stop_mcp_server():
    """停止 MCP Socket Server。"""
    global _server_running, _server_thread, _server_socket

    if not _server_running:
        print("[MayaMCP] 服务器未在运行")
        return

    _server_running = False
    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass
    if _server_thread:
        _server_thread.join(timeout=5)
        _server_thread = None
    print("[MayaMCP] 服务器已停止")


def restart_mcp_server(host=HOST, port=PORT):
    """重启 MCP Socket Server。"""
    stop_mcp_server()
    import time
    time.sleep(0.5)
    start_mcp_server(host, port)


# ============================================================
# 自动启动
# ============================================================
start_mcp_server()
