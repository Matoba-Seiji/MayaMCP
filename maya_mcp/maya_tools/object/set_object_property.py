#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 设置 Maya 节点属性


def set_object_property(object_name: str, attribute: str, value: str) -> dict:
    """设置对象某个属性的值（自动按属性类型转换）。

    Args:
        object_name: 目标对象名称。
        attribute: 属性名，如 "translateX"、"visibility"、"radius"。
        value: 属性值字符串。布尔用 "true"/"false"；数值直接写；
               多通道用逗号分隔，如 "1,2,3"。

    Returns:
        dict: success / name / attribute / value / message。

    示例调用:
        set_object_property(object_name="pSphere1", attribute="visibility", value="false")
        set_object_property(object_name="pCube1", attribute="translateY", value="5")
    """
    import maya.cmds as cmds
    import traceback

    try:
        plug = f"{object_name}.{attribute}"
        if not cmds.objExists(object_name):
            return {"success": False, "message": f"未找到对象 '{object_name}'。"}
        if not cmds.attributeQuery(attribute, node=object_name, exists=True):
            return {"success": False, "message": f"对象 '{object_name}' 不存在属性 '{attribute}'。"}

        v = value.strip()
        if "," in v:
            nums = [float(x.strip()) for x in v.split(",")]
            cmds.setAttr(plug, *nums, type="double3") if len(nums) == 3 else cmds.setAttr(plug, *nums)
        elif v.lower() in ("true", "false"):
            cmds.setAttr(plug, v.lower() == "true")
        else:
            try:
                num = float(v)
                cmds.setAttr(plug, int(num) if num.is_integer() else num)
            except ValueError:
                cmds.setAttr(plug, v, type="string")

        new_val = cmds.getAttr(plug)
        return {"success": True, "name": object_name, "attribute": attribute, "value": new_val,
                "message": f"已设置 {plug} = {new_val}。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"设置属性失败: {str(e)}", "traceback": traceback.format_exc()}
