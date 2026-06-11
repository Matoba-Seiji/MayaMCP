#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 创建 Maya 材质


def create_material(name: str = "", material_type: str = "lambert", color: str = "") -> dict:
    """创建一个材质并连接 shadingEngine。

    Args:
        name: 材质名称。为空使用默认命名。
        material_type: 材质类型，如 "lambert"、"blinn"、"phong"、"standardSurface"、"aiStandardSurface"。
        color: 基础颜色 "r,g,b"（0-1 范围），如 "1,0,0"。为空使用默认颜色。

    Returns:
        dict: success / material / shading_engine / message。

    示例调用:
        create_material(material_type="blinn", color="1,0,0")
        create_material(name="myRed", material_type="standardSurface", color="0.8,0.1,0.1")
    """
    import maya.cmds as cmds
    import traceback

    try:
        kwargs = {"asShader": True}
        if name and name.strip():
            kwargs["name"] = name.strip()
        mat = cmds.shadingNode(material_type, **kwargs)

        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{mat}SG")
        cmds.connectAttr(f"{mat}.outColor", f"{sg}.surfaceShader", force=True)

        applied_color = None
        if color.strip():
            try:
                c = [float(x.strip()) for x in color.split(",")]
                if len(c) == 3:
                    color_attr = "baseColor" if cmds.attributeQuery("baseColor", node=mat, exists=True) else "color"
                    cmds.setAttr(f"{mat}.{color_attr}", c[0], c[1], c[2], type="double3")
                    applied_color = c
            except Exception:
                pass

        return {"success": True, "material": mat, "shading_engine": sg, "color": applied_color,
                "message": f"已创建 {material_type} 材质 '{mat}'。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"创建材质失败: {str(e)}", "traceback": traceback.format_exc()}
