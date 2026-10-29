#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Maya MCP Server 命令行入口。

支持:
    python -m maya_mcp
    python -m maya_mcp --port 50017
    uvx maya-mcp

--port 用于在同一台机器上连接不同的 Maya 实例；未指定时读取
MAYAMCP_PORT 环境变量，再回退到默认端口 50016。
"""

import argparse

from .server import main


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m maya_mcp",
        description="Maya MCP stdio server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="in-Maya listener TCP port (default: MAYAMCP_PORT env or 50016)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="in-Maya listener host (default: 127.0.0.1)",
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    main(port=args.port, host=args.host)
