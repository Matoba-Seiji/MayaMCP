#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Maya Socket 通信层。

适配 Maya 的 Socket 通信协议，直接发送 Python 代码执行。
"""

# Import built-in modules
import socket
import json
import logging
import struct

logger = logging.getLogger("MayaMCPServer")

# ============================================================
# 通信协议
#   发送: [4字节 大端序 uint32: 消息体长度] + [UTF-8编码的Python脚本]
#   接收: [4字节 大端序 uint32: 消息体长度] + [UTF-8编码的JSON结果字符串]
# Maya 端需运行 maya_server_listener.py 监听脚本。
# ============================================================

HEADER_SIZE = 4
DEFAULT_RECV_BUFSIZE = 4096
SOCKET_TIMEOUT = 120


def _pack_message(data: str) -> bytes:
    encoded = data.encode('utf-8')
    header = struct.pack('>I', len(encoded))
    return header + encoded


def _recv_all(sock: socket.socket) -> str:
    """从 Socket 接收完整的带长度头的消息。"""
    header_data = b''
    while len(header_data) < HEADER_SIZE:
        chunk = sock.recv(HEADER_SIZE - len(header_data))
        if not chunk:
            raise ConnectionError("Maya 端连接已关闭，未能读取消息头。")
        header_data += chunk

    msg_length = struct.unpack('>I', header_data)[0]
    if msg_length == 0:
        return ''

    body_data = b''
    while len(body_data) < msg_length:
        remaining = msg_length - len(body_data)
        chunk = sock.recv(min(remaining, DEFAULT_RECV_BUFSIZE))
        if not chunk:
            raise ConnectionError(
                f"Maya 端连接已关闭，消息体不完整。期望 {msg_length} 字节，实际收到 {len(body_data)} 字节。"
            )
        body_data += chunk

    return body_data.decode('utf-8')


class MayaConnection(object):
    """Maya Socket 通信连接器。

    通过 TCP Socket 连接到 Maya 内运行的 Python Socket Server，
    发送 Python 脚本并接收执行结果。
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 50011):
        super(MayaConnection, self).__init__()
        self._host = host
        self._port = port

    def _send_python_command(self, python_script: str) -> str:
        """通过 Socket 将 Python 脚本发送给 Maya 并读取返回结果。"""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(SOCKET_TIMEOUT)
        try:
            client.connect((self._host, self._port))
            logger.debug(f"已连接到 Maya ({self._host}:{self._port})")

            client.sendall(_pack_message(python_script))
            logger.debug(f"已发送脚本，长度: {len(python_script)} 字符")

            result = _recv_all(client)
            logger.debug(f"收到结果，长度: {len(result)} 字符")
            return result

        except ConnectionRefusedError:
            error_msg = (
                f"无法连接到 Maya ({self._host}:{self._port})。"
                f"请确保 Maya 已启动，且 maya_server_listener.py 监听脚本正在运行。"
            )
            logger.error(error_msg)
            raise ConnectionRefusedError(error_msg)
        except socket.timeout:
            error_msg = f"等待 Maya 响应超时（{SOCKET_TIMEOUT}秒）。脚本可能执行时间过长。"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"与 Maya 通信出错: {e}")
            raise
        finally:
            client.close()

    def run_python_script(self, python_script: str):
        """Execute a script and return the JSON result produced by Maya."""
        python_script = "_mcp_maya_results = None\n" + python_script

        result = self._send_python_command(python_script)
        logger.debug(f"send_python_command result: {result[:500] if result else result}")

        if result:
            result = result.strip()

        if not result or result in ('', 'None', '\n'):
            logger.debug("首次结果为空，尝试读取 _mcp_maya_results 变量")
            result = self._send_python_command("_mcp_maya_results")
            if result:
                result = result.strip()

        if result:
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                logger.debug(f"结果无法解析为 JSON，按原样返回: {result[:200] if result else result}")

        return result
