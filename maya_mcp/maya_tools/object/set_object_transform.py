#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 设置 Maya 对象的变换


def set_object_transform(object_name: str, translate: str = "", rotate: str = "", scale: str = "",
                         world_space: bool = True) -> dict:
    """设置对象的平移/旋转/缩放。仅设置传入的项，留空的项保持不变。

    Args:
        object_name: 目标对象名称。
        translate: 平移 "x,y,z"，留空不修改。
        rotate: 旋转欧拉角(度) "x,y,z"，留空不修改。
        scale: 缩放 "x,y,z"，留空不修改。
        world_space: True 使用世界空间，False 使用对象空间（仅对 translate/rotate 有效）。默认 True。

    Returns:
        dict: success / name / transform / message。

    示例调用:
        set_object_transform(object_name="pCube1", translate="5,0,0")
        set_object_transform(object_name="pCube1", rotate="0,45,0", scale="2,2,2")
    """
    import maya.cmds as cmds
    import traceback

    def _parse(s):
        parts = [float(p.strip()) for p in s.split(",")]
        if len(parts) != 3:
            raise ValueError(f"需要 3 个数值，得到 {len(parts)} 个")
        return parts

    try:
        if not cmds.objExists(object_name):
            return {"success": False, "message": f"未找到对象 '{object_name}'。"}

        if translate.strip():
            t = _parse(translate)
            cmds.xform(object_name, translation=t, worldSpace=world_space, objectSpace=not world_space)
        if rotate.strip():
            r = _parse(rotate)
            cmds.xform(object_name, rotation=r, worldSpace=world_space, objectSpace=not world_space)
        if scale.strip():
            s = _parse(scale)
            cmds.xform(object_name, scale=s)

        t = cmds.xform(object_name, query=True, worldSpace=True, translation=True)
        r = cmds.xform(object_name, query=True, worldSpace=True, rotation=True)
        sc = cmds.xform(object_name, query=True, relative=True, scale=True)
        transform = {
            "translate": [float(v) for v in t],
            "rotate": [float(v) for v in r],
            "scale": [float(v) for v in sc],
        }
        return {"success": True, "name": object_name, "transform": transform,
                "message": f"已更新 '{object_name}' 的变换。"}
    except ValueError as e:
        return {"success": False, "message": f"参数格式错误: {str(e)}，请使用 'x,y,z' 格式。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"设置变换失败: {str(e)}", "traceback": traceback.format_exc()}
