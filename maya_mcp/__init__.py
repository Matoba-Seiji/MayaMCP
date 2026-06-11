#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Maya MCP Server - 通过 MCP 协议远程控制 Maya。"""

__version__ = "0.1.0"

from .server import main

__all__ = ["main", "__version__"]
