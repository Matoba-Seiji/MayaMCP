#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 重命名 Maya 对象


def rename_object(object_name: str, new_name: str) -> dict:
    """重命名场景中的对象。

    Args:
        object_name: 当前对象名称。
        new_name: 新名称。

    Returns:
        dict: success / old_name / new_name / message。

    示例调用:
        rename_object(object_name="pCube1", new_name="myBox")
    """
    import maya.cmds as cmds
    import traceback

    try:
        if not cmds.objExists(object_name):
            return {"success": False, "message": f"未找到对象 '{object_name}'。"}
        result = cmds.rename(object_name, new_name)
        return {"success": True, "old_name": object_name, "new_name": result,
                "message": f"已将 '{object_name}' 重命名为 '{result}'。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"重命名失败: {str(e)}", "traceback": traceback.format_exc()}
