#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""管理工具脚本与 MCP Tool 的注册信息。"""

# Import built-in modules
import os
import inspect
import logging
import importlib.util
from typing import Optional, List, get_origin, Any
# Import third-party modules
from mcp.types import Tool
from mcp.server.fastmcp.utilities.func_metadata import func_metadata
from mcp.server.fastmcp.server import Context
# Import local modules
logger = logging.getLogger("MayaMCPServer")

__all__ = ["OperationsManager"]


def _get_function_tool(tool_name: str, filename: str) -> Optional[Tool]:
    """从脚本中解析与文件同名的函数并构建 MCP Tool 描述对象。

    Args:
        tool_name: 工具名（即文件名）。
        filename: 脚本文件路径。

    Returns:
        构建好的 Tool，解析失败返回 None。
    """
    try:
        spec = importlib.util.spec_from_file_location(tool_name, filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, tool_name)
    except Exception as e:
        logger.error(f"Unable to pre-load {tool_name} because: {e}")
        return None

    func_doc = fn.__doc__ or ""
    sig = inspect.signature(fn)
    context_kwarg = None
    for param_name, param in sig.parameters.items():
        if get_origin(param.annotation) is not None:
            continue
        if param.annotation is Any:
            continue
        if not isinstance(param.annotation, type):
            continue
        if issubclass(param.annotation, Context):
            context_kwarg = param_name
            break

    func_arg_metadata = func_metadata(fn, skip_names=[context_kwarg] if context_kwarg is not None else [])
    parameters = func_arg_metadata.arg_model.model_json_schema()

    return Tool(name=tool_name, description=func_doc, inputSchema=parameters)


class OperationsManager(object):
    def __init__(self, script_directory: str):
        """初始化工具与路径映射表。

        Args:
            script_directory: 需要扫描的脚本目录。
        """
        self._script_directory = script_directory
        self._paths = {}
        self._tools = {}

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_file_path(self, name: str) -> Optional[str]:
        return self._paths.get(name)

    def get_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def find_tools(self):
        """扫描目录，加载所有可用的工具脚本。"""
        for root, dirs, files in os.walk(self._script_directory):
            for file in files:
                if not file.endswith(".py") or file.startswith("__"):
                    continue
                name, _ = os.path.splitext(file)
                path = os.path.join(root, file)
                tool = _get_function_tool(name, path)
                if not tool:
                    continue
                self._paths[name] = path
                self._tools[name] = tool
