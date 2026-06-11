#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 导出 Maya 对象到文件


def export_file(file_path: str, selected_only: bool = False, file_type: str = "") -> dict:
    """将当前场景或所选对象导出到文件。

    Args:
        file_path: 导出目标完整路径。
        selected_only: True 仅导出当前选中对象，False 导出整个场景。默认 False。
        file_type: 导出类型，留空则按扩展名推断。可选: mayaAscii/mayaBinary/FBX export/OBJexport。

    Returns:
        dict: success / file_path / message。

    示例调用:
        export_file(file_path="D:/out/scene.mb")
        export_file(file_path="D:/out/sel.fbx", selected_only=True)
    """
    import maya.cmds as cmds
    import traceback

    try:
        if not file_type:
            ext = file_path.lower().rsplit(".", 1)[-1]
            file_type = {
                "ma": "mayaAscii", "mb": "mayaBinary",
                "fbx": "FBX export", "obj": "OBJexport",
            }.get(ext, "mayaBinary")

        if selected_only:
            if not cmds.ls(selection=True):
                return {"success": False, "message": "没有选中任何对象，无法导出选中项。"}
            saved = cmds.file(file_path, exportSelected=True, type=file_type, force=True)
        else:
            saved = cmds.file(file_path, exportAll=True, type=file_type, force=True)

        return {"success": True, "file_path": saved, "message": f"已导出到: {saved}"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"导出文件失败: {str(e)}", "traceback": traceback.format_exc()}
