#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 列出场景中的对象


def list_objects(object_type: str = "", pattern: str = "", limit: int = 200) -> dict:
    """列出当前场景中的对象，可按类型与名称模式过滤。

    Args:
        object_type: 节点类型过滤，如 "mesh"、"transform"、"joint"、"camera"。
                     为空则列出所有 DAG 变换节点。
        pattern: 名称通配模式，如 "pCube*"。为空表示不按名称过滤。
        limit: 返回数量上限，默认 200。

    Returns:
        dict: success / count / objects(list) / message。

    示例调用:
        list_objects()
        list_objects(object_type="mesh")
        list_objects(pattern="pSphere*")
    """
    import maya.cmds as cmds
    import traceback

    try:
        kwargs = {"long": False}
        if object_type:
            kwargs["type"] = object_type
        else:
            kwargs["type"] = "transform"

        if pattern:
            objs = cmds.ls(pattern, **kwargs) or []
        else:
            objs = cmds.ls(**kwargs) or []

        total = len(objs)
        objs = objs[:max(1, int(limit))]
        return {
            "success": True,
            "count": total,
            "objects": objs,
            "message": f"找到 {total} 个对象" + (f"（返回前 {len(objs)} 个）" if total > len(objs) else "") + "。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"列出对象失败: {str(e)}", "traceback": traceback.format_exc()}
