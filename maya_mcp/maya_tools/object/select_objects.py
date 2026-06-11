#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 选择 Maya 对象


def select_objects(object_names: str = "", clear: bool = False) -> dict:
    """选择场景中的对象，或清空当前选择。

    Args:
        object_names: 要选择的对象名称，多个用逗号分隔。为空且 clear=False 时返回当前选择。
        clear: True 则清空选择（忽略 object_names）。默认 False。

    Returns:
        dict: success / selected(list) / message。

    示例调用:
        select_objects(object_names="pCube1,pSphere1")
        select_objects(clear=True)
        select_objects()
    """
    import maya.cmds as cmds
    import traceback

    try:
        if clear:
            cmds.select(clear=True)
            return {"success": True, "selected": [], "message": "已清空选择。"}

        if not object_names.strip():
            sel = cmds.ls(selection=True) or []
            return {"success": True, "selected": sel, "message": f"当前选中 {len(sel)} 个对象。"}

        names = [n.strip() for n in object_names.split(",") if n.strip()]
        valid = [n for n in names if cmds.objExists(n)]
        missing = [n for n in names if not cmds.objExists(n)]
        if not valid:
            return {"success": False, "message": f"没有找到可选择的对象: {names}"}

        cmds.select(valid, replace=True)
        sel = cmds.ls(selection=True) or []
        msg = f"已选择 {len(sel)} 个对象。"
        if missing:
            msg += f" 未找到: {missing}"
        return {"success": True, "selected": sel, "message": msg}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"选择对象失败: {str(e)}", "traceback": traceback.format_exc()}
