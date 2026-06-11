#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 新建 Maya 场景


def new_scene(force: bool = True) -> dict:
    """新建一个空白 Maya 场景。

    Args:
        force: 是否强制新建（不提示保存当前未保存的修改）。默认 True。

    Returns:
        dict: success / message。

    示例调用:
        new_scene()
    """
    import maya.cmds as cmds
    import traceback

    try:
        cmds.file(new=True, force=bool(force))
        return {"success": True, "message": "已新建空白场景。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"新建场景失败: {str(e)}", "traceback": traceback.format_exc()}
