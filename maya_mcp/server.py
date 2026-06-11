#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Maya MCP Server 核心服务模块。

负责工具注册与发现、脚本生成、发送至 Maya、MCP 协议通信。
"""

# Import built-in modules
import os
import json
import asyncio
import traceback
from pprint import pformat
from itertools import chain
from typing import Sequence, List, Any, Dict

# Import third-party modules
import mcp.server.stdio
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.fastmcp.utilities.types import Image
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import pydantic_core

# Import local modules
from maya_mcp.connector.maya_connection import MayaConnection
from maya_mcp.OperationManager import OperationsManager
from maya_mcp.log import LogManager, log_file

logger = LogManager.get_logger('MayaMCPServer', __file__, log_file)

__version__ = "0.1.0"  # 修改版本号时需同步更新 pyproject.toml 和 __init__.py

# Maya 监听端口（与 3dsMaxMCP 的 50007 区分，避免冲突）
MAYA_HOST = '127.0.0.1'
MAYA_PORT = 50011


class OperationFactory:
    @classmethod
    def get_operation_manager(cls, engine: str):
        tool_directory = os.path.abspath(
            os.path.join(os.path.dirname(__file__), f"{engine}_tools").replace("\\", "/")
        )
        manager = OperationsManager(tool_directory)
        manager.find_tools()
        return manager


async def run(server: Server, server_name: str):
    """启动 MCP Server 并在 stdio 通道上提供服务。"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=server_name,
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                ),
            )
        )


def convert_to_content(result: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """将结果统一转换为 MCP 内容对象列表。"""
    if result is None:
        return []
    if isinstance(result, TextContent | ImageContent | EmbeddedResource):
        return [result]
    if isinstance(result, Image):
        return [result.to_image_content()]
    if isinstance(result, list | tuple):
        return list(chain.from_iterable(convert_to_content(item) for item in result))
    if not isinstance(result, str):
        try:
            result = json.dumps(pydantic_core.to_jsonable_python(result))
        except Exception:
            result = str(result)
    return [TextContent(type="text", text=result)]


def wrap_script_in_scoped_function(python_script: str, tool_name: str, args: List[str]) -> str:
    """将工具脚本包装为带异常捕获与 JSON 结果处理的作用域函数。"""
    spaced_python_script = '    ' + python_script.replace('\n', '\n    ')
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../")).replace("\\", "/")
    arg_list = ','.join(args)
    kwargs = ','.join([a + '=' + a for a in args])
    return f"""
def _add_root_dir_to_env():
    import sys
    if "{root_dir}" not in sys.path:
        sys.path.append("{root_dir}")
def _mcp_maya_scope({arg_list}):
    import json
    import traceback
    from pprint import pprint
    _add_root_dir_to_env()
{spaced_python_script}
    try:
        results = {tool_name}({kwargs})
    except Exception as e:
        traceback.print_exc()
        results = dict([('success', False), ('message', 'Error: Maya tool failed with the follow message: ' + str(e))])

    if results and not isinstance(results, str):
        try:
            results = json.dumps(results)
        except Exception:
            print("MayaMCP: Error attempting to return results from tool {tool_name} as JSON")
            pprint(results)
            return str(results)
    return results
"""


def load_maya_tool_source(tool_name: str, filename: str, args: Dict[str, Any] = None, *, log: bool = False) -> str:
    """读取工具脚本并生成可执行的 Maya Python 调用脚本。"""
    args = args or {}
    with open(filename, 'r', encoding='utf-8') as f:
        script = f.read()
    results = wrap_script_in_scoped_function(script, tool_name, args.keys())
    results += "\n_mcp_maya_results = _mcp_maya_scope("
    params = []
    for k, v in args.items():
        if isinstance(v, str):
            params.append(f"{k}='''{v}'''")
        else:
            params.append(f"{k}={v}")
    results += ','.join(params)
    results += ")\n\n"

    if log:
        logger.debug(results)
    return results


def main():
    """MCP Server 入口函数。"""
    server_name = "MayaMCP"
    operation_manager = OperationFactory.get_operation_manager("maya")
    server = Server(server_name)

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        logger.info("Requesting a list of tools.")
        return operation_manager.get_tools()

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        logger.info(f"Calling tool {name} with arguments: {pformat(arguments)}")

        path = operation_manager.get_file_path(name)
        if not path:
            error_msg = f"Tool {name} not found."
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        try:
            maya_conn = MayaConnection(MAYA_HOST, MAYA_PORT)
            python_script = load_maya_tool_source(name, path, arguments)
            results = maya_conn.run_python_script(python_script)
            converted_results = convert_to_content(results)
        except Exception as e:
            error_msg = f"Error: tool {name} failed to run. Path {path} Reason {e}\n traceback:{traceback.format_exc()}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        if converted_results:
            return converted_results
        return {"success": True}

    asyncio.run(run(server, server_name))


if __name__ == '__main__':
    main()
