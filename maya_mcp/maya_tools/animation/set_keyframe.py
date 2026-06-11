#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 设置 Maya 关键帧


def set_keyframe(object_name: str, attribute: str, frame: float, value: str = "") -> dict:
    """在指定帧为对象的某个属性设置关键帧。

    Args:
        object_name: 目标对象名称。
        attribute: 属性名，如 "translateX"、"rotateY"。
        frame: 帧号。
        value: 该帧的属性值。为空则使用属性的当前值打关键帧。

    Returns:
        dict: success / name / attribute / frame / value / message。

    示例调用:
        set_keyframe(object_name="pCube1", attribute="translateX", frame=1, value="0")
        set_keyframe(object_name="pCube1", attribute="translateX", frame=24, value="10")
    """
    import maya.cmds as cmds
    import traceback

    try:
        if not cmds.objExists(object_name):
            return {"success": False, "message": f"未找到对象 '{object_name}'。"}
        if not cmds.attributeQuery(attribute, node=object_name, exists=True):
            return {"success": False, "message": f"对象 '{object_name}' 不存在属性 '{attribute}'。"}

        kwargs = dict(attribute=attribute, time=frame)
        applied_value = None
        if value.strip():
            applied_value = float(value)
            kwargs["value"] = applied_value
        cmds.setKeyframe(object_name, **kwargs)

        if applied_value is None:
            applied_value = cmds.getAttr(f"{object_name}.{attribute}")

        return {"success": True, "name": object_name, "attribute": attribute, "frame": frame,
                "value": applied_value, "message": f"已在第 {frame} 帧为 {object_name}.{attribute} 设置关键帧 (值={applied_value})。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"设置关键帧失败: {str(e)}", "traceback": traceback.format_exc()}
