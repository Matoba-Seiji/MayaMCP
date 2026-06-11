#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 删除 Maya 对象


def delete_object(object_names: str) -> dict:
    """删除场景中的一个或多个对象。

    Args:
        object_names: 要删除的对象名称，多个用逗号分隔，如 "pCube1,pSphere1"。

    Returns:
        dict: success / deleted(list) / not_found(list) / message。

    示例调用:
        delete_object(object_names="pCube1")
        delete_object(object_names="pCube1,pSphere1")
    """
    import maya.cmds as cmds
    import traceback

    try:
        names = [n.strip() for n in object_names.split(",") if n.strip()]
        if not names:
            return {"success": False, "message": "未提供任何对象名称。"}

        deleted, not_found = [], []
        for n in names:
            if cmds.objExists(n):
                cmds.delete(n)
                deleted.append(n)
            else:
                not_found.append(n)

        return {
            "success": len(deleted) > 0,
            "deleted": deleted,
            "not_found": not_found,
            "message": f"已删除 {len(deleted)} 个对象" + (f"，{len(not_found)} 个未找到: {not_found}" if not_found else "") + "。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"删除对象失败: {str(e)}", "traceback": traceback.format_exc()}
