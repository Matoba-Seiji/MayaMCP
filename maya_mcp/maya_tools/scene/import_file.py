#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 导入文件到 Maya 当前场景


def import_file(file_path: str, namespace: str = "") -> dict:
    """将外部文件导入当前 Maya 场景（支持 .ma/.mb/.fbx/.obj 等）。

    Args:
        file_path: 要导入的文件完整路径。
        namespace: 导入使用的命名空间。为空则不使用命名空间。

    Returns:
        dict: success / file_path / new_nodes / message。

    示例调用:
        import_file(file_path="D:/assets/prop.fbx")
        import_file(file_path="D:/assets/char.mb", namespace="char")
    """
    import maya.cmds as cmds
    import os
    import traceback

    try:
        if not os.path.isfile(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}"}

        kwargs = dict(i=True, returnNewNodes=True, ignoreVersion=True)
        if namespace:
            kwargs["namespace"] = namespace
        else:
            kwargs["renameAll"] = False

        new_nodes = cmds.file(file_path, **kwargs) or []
        return {
            "success": True,
            "file_path": file_path,
            "new_nodes": list(new_nodes)[:200],
            "message": f"已导入 {file_path}，新增 {len(new_nodes)} 个节点。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"导入文件失败: {str(e)}", "traceback": traceback.format_exc()}
