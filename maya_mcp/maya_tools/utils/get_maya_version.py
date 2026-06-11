#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 获取 Maya 版本信息


def get_maya_version() -> dict:
    """获取当前运行的 Maya 版本信息。

    Returns:
        dict: success / version / api_version / product / message。

    示例调用:
        get_maya_version()
    """
    import maya.cmds as cmds
    import traceback

    try:
        version = cmds.about(version=True)
        api_version = cmds.about(apiVersion=True)
        product = cmds.about(product=True)
        return {"success": True, "version": version, "api_version": api_version, "product": product,
                "message": f"{product} (version {version}, api {api_version})。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"获取 Maya 版本失败: {str(e)}", "traceback": traceback.format_exc()}
