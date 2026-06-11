#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 把材质指定给对象


def assign_material(object_names: str, material_name: str) -> dict:
    """将已有材质指定给一个或多个对象。

    Args:
        object_names: 目标对象名称，多个用逗号分隔。
        material_name: 材质节点名称（surface shader）。

    Returns:
        dict: success / assigned(list) / material / message。

    示例调用:
        assign_material(object_names="pCube1,pSphere1", material_name="lambert2")
    """
    import maya.cmds as cmds
    import traceback

    try:
        if not cmds.objExists(material_name):
            return {"success": False, "message": f"未找到材质 '{material_name}'。"}

        # 找到或创建该材质的 shadingEngine
        sgs = cmds.listConnections(f"{material_name}.outColor", type="shadingEngine") or []
        if sgs:
            sg = sgs[0]
        else:
            sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{material_name}SG")
            cmds.connectAttr(f"{material_name}.outColor", f"{sg}.surfaceShader", force=True)

        names = [n.strip() for n in object_names.split(",") if n.strip()]
        assigned, not_found = [], []
        for n in names:
            if cmds.objExists(n):
                cmds.sets(n, edit=True, forceElement=sg)
                assigned.append(n)
            else:
                not_found.append(n)

        return {
            "success": len(assigned) > 0,
            "assigned": assigned,
            "material": material_name,
            "not_found": not_found,
            "message": f"已将 '{material_name}' 指定给 {len(assigned)} 个对象" +
                       (f"，未找到: {not_found}" if not_found else "") + "。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"指定材质失败: {str(e)}", "traceback": traceback.format_exc()}
