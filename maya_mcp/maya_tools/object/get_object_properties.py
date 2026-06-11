#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 获取 Maya 对象的详细属性


def get_object_properties(object_name: str) -> dict:
    """获取场景中指定对象的详细属性信息。

    返回类型、变换、可见性、网格统计、所属材质等。

    Args:
        object_name: 目标对象名称。

    Returns:
        dict: success / name / node_type / shape_type / transform / visibility
              / vertex_count / face_count / materials(list) / message。

    示例调用:
        get_object_properties(object_name="pCube1")
    """
    import maya.cmds as cmds
    import traceback

    try:
        if not cmds.objExists(object_name):
            return {"success": False, "message": f"未找到对象 '{object_name}'。"}

        node_type = cmds.nodeType(object_name)
        shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True) or []
        shape_type = cmds.nodeType(shapes[0]) if shapes else ""

        t = cmds.xform(object_name, query=True, worldSpace=True, translation=True)
        r = cmds.xform(object_name, query=True, worldSpace=True, rotation=True)
        sc = cmds.xform(object_name, query=True, relative=True, scale=True)
        transform = {
            "translate": [float(v) for v in t],
            "rotate": [float(v) for v in r],
            "scale": [float(v) for v in sc],
        }

        try:
            visibility = bool(cmds.getAttr(f"{object_name}.visibility"))
        except Exception:
            visibility = True

        vertex_count = face_count = 0
        if shape_type == "mesh":
            try:
                vertex_count = int(cmds.polyEvaluate(object_name, vertex=True))
                face_count = int(cmds.polyEvaluate(object_name, face=True))
            except Exception:
                pass

        materials = []
        try:
            for shp in shapes:
                sgs = cmds.listConnections(shp, type="shadingEngine") or []
                for sg in set(sgs):
                    mats = cmds.listConnections(f"{sg}.surfaceShader") or []
                    materials.extend(mats)
            materials = list(set(materials))
        except Exception:
            pass

        return {
            "success": True,
            "name": object_name,
            "node_type": node_type,
            "shape_type": shape_type,
            "transform": transform,
            "visibility": visibility,
            "vertex_count": vertex_count,
            "face_count": face_count,
            "materials": materials,
            "message": f"对象 '{object_name}' (类型 {shape_type or node_type})，位置 {t}，"
                       f"顶点 {vertex_count}，面 {face_count}，材质 {materials if materials else '无'}。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"获取对象属性失败: {str(e)}", "traceback": traceback.format_exc()}
