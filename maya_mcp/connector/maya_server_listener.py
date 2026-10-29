#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Maya 内部 Socket Server 监听脚本。

每个 Maya 进程各自运行一个监听器，用端口区分实例（默认 50016）：
- 菜单 “启动监听（实例1·50016）” / “启动监听（实例2·50017）”；
- 也可用 MAYAMCP_PORT 环境变量指定默认端口；
- MCP 桥接端用 `python -m maya_mcp --port <端口>` 连接对应实例。

启动后在后台线程监听 TCP 端口，接收来自 MCP Server 的 Python 脚本，
通过 maya.utils.executeInMainThreadWithResult 调度到 **主线程** 执行
（保证 maya.cmds 可用），执行完成后将结果返回。

通信协议:
    请求: [4字节大端序uint32: 消息体长度] + [UTF-8编码的Python脚本]
    响应: [4字节大端序uint32: 消息体长度] + [UTF-8编码的结果字符串]
"""

import json
import os
import socket
import struct
import threading
import traceback

import maya.utils

# ============================================================
# 配置
# ============================================================
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 50016
PORT_ENV_VAR = 'MAYAMCP_PORT'
HEADER_SIZE = 4
RECV_BUFSIZE = 4096


def _port_from_env(default=DEFAULT_PORT):
    """Resolve the listener port: MAYAMCP_PORT environment variable wins."""
    raw = os.environ.get(PORT_ENV_VAR)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if 0 < value < 65536 else default


HOST = DEFAULT_HOST
PORT = _port_from_env()

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


def _server_loop(server_socket):
    global _server_running, _server_socket

    try:
        while _server_running:
            try:
                conn, addr = server_socket.accept()
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
        try:
            server_socket.close()
        except Exception:
            pass
        if _server_socket is server_socket:
            _server_socket = None
            _server_running = False
        print("[MayaMCP] Socket Server 已停止")


# ============================================================
# 公共 API
# ============================================================
def is_running():
    """当前进程内的监听器是否在运行。"""
    if not (_server_running and _server_socket and _server_thread):
        return False
    return bool(_server_thread.is_alive())


def start_mcp_server(host=None, port=None):
    """启动 MCP Socket Server。

    host / port 为 None 时使用 MAYAMCP_PORT 环境变量或默认的
    127.0.0.1:50016。已在其他端口运行时会自动切换到目标端口，
    因此同一个 Maya 进程始终只监听一个端口。
    """
    global _server_running, _server_thread, _server_socket, HOST, PORT

    target_host = HOST if host is None else host
    target_port = PORT if port is None else int(port)

    if is_running():
        if str(HOST) == str(target_host) and int(PORT) == int(target_port):
            print(f"[MayaMCP] 服务器已在运行中 ({HOST}:{PORT})")
            return True

    # Bind the new endpoint before stopping the old one, so a failed switch
    # (e.g. the target port is occupied by another app) keeps the working
    # listener alive.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.settimeout(1.0)
        server_socket.bind((target_host, target_port))
        server_socket.listen(5)
    except Exception as exc:
        try:
            server_socket.close()
        except Exception:
            pass
        print(f"[MayaMCP] 启动失败：无法监听 {target_host}:{target_port} ({exc})")
        return False

    if is_running():
        stop_mcp_server()

    HOST = target_host
    PORT = target_port
    _server_socket = server_socket
    _server_running = True
    _server_thread = threading.Thread(target=_server_loop, args=(server_socket,), daemon=True)
    _server_thread.start()
    print(f"[MayaMCP] Socket Server 已启动，监听 {HOST}:{PORT}")
    print("[MayaMCP] 等待 MCP Server 连接...")
    return True


def stop_mcp_server():
    """停止 MCP Socket Server。"""
    global _server_running, _server_thread, _server_socket

    if not _server_running:
        print("[MayaMCP] 服务器未在运行")
        return False

    _server_running = False
    if _server_socket:
        try:
            _server_socket.close()
        except Exception:
            pass
        _server_socket = None
    if _server_thread:
        _server_thread.join(timeout=5)
        _server_thread = None
    print("[MayaMCP] 服务器已停止")
    return True


def restart_mcp_server(host=None, port=None):
    """重启 MCP Socket Server；port 为 None 时沿用当前端口。"""
    if port is None and is_running():
        port = PORT
    stop_mcp_server()
    import time
    time.sleep(0.5)
    return start_mcp_server(host, port)


# ============================================================
# 自动启动（导入即启动默认端口，与既有用法保持一致）
# ============================================================
start_mcp_server()
