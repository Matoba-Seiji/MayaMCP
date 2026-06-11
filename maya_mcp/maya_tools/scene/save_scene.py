#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 保存 Maya 场景


def save_scene(file_path: str = "") -> dict:
    """保存当前 Maya 场景。

    Args:
        file_path: 另存为的目标路径（.ma 或 .mb）。为空则保存到当前文件，
                   若当前场景从未保存过且 file_path 为空，则返回失败。

    Returns:
        dict: success / file_path / message。

    示例调用:
        save_scene()
        save_scene(file_path="D:/scenes/test.mb")
    """
    import maya.cmds as cmds
    import traceback

    try:
        if file_path:
            ext = file_path.lower().rsplit(".", 1)[-1]
            file_type = "mayaBinary" if ext == "mb" else "mayaAscii"
            cmds.file(rename=file_path)
            saved = cmds.file(save=True, type=file_type)
        else:
            current = cmds.file(query=True, sceneName=True)
            if not current:
                return {"success": False, "message": "当前场景尚未保存过，请提供 file_path 指定保存路径。"}
            saved = cmds.file(save=True)
        return {"success": True, "file_path": saved, "message": f"已保存场景: {saved}"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"保存场景失败: {str(e)}", "traceback": traceback.format_exc()}
