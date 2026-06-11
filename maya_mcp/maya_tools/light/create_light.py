#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 创建 Maya 灯光


def create_light(light_type: str = "directional", name: str = "", position: str = "0,5,0",
                 intensity: float = 1.0) -> dict:
    """在场景中创建一盏灯光。

    Args:
        light_type: 灯光类型，可选 "directional"/"point"/"spot"/"area"/"ambient"/"volume"。
        name: 灯光名称。为空使用默认命名。
        position: 灯光位置 "x,y,z"，默认 "0,5,0"。
        intensity: 灯光强度，默认 1.0。

    Returns:
        dict: success / name / light_type / position / intensity / message。

    示例调用:
        create_light(light_type="point", position="0,10,0", intensity=2.0)
    """
    import maya.cmds as cmds
    import traceback

    try:
        fn_map = {
            "directional": cmds.directionalLight,
            "point": cmds.pointLight,
            "spot": cmds.spotLight,
            "ambient": cmds.ambientLight,
            "area": cmds.shadingNode,
            "volume": cmds.shadingNode,
        }
        key = light_type.strip().lower()
        if key not in fn_map:
            return {"success": False, "message": f"不支持的 light_type '{light_type}'。"}

        if key in ("area", "volume"):
            shape = cmds.shadingNode(f"{key}Light", asLight=True)
            transform = cmds.listRelatives(shape, parent=True)[0]
        else:
            shape = fn_map[key](intensity=intensity)
            transform = cmds.listRelatives(shape, parent=True)[0] if cmds.listRelatives(shape, parent=True) else shape

        if name and name.strip():
            transform = cmds.rename(transform, name.strip())

        try:
            pos = [float(p.strip()) for p in position.split(",")]
            if len(pos) == 3:
                cmds.move(pos[0], pos[1], pos[2], transform, absolute=True)
        except Exception:
            pos = [0, 5, 0]

        try:
            shp = cmds.listRelatives(transform, shapes=True)[0]
            cmds.setAttr(f"{shp}.intensity", intensity)
        except Exception:
            pass

        actual = cmds.xform(transform, query=True, worldSpace=True, translation=True)
        return {"success": True, "name": transform, "light_type": light_type,
                "position": [float(v) for v in actual], "intensity": intensity,
                "message": f"已创建 {light_type} 灯光 '{transform}'。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"创建灯光失败: {str(e)}", "traceback": traceback.format_exc()}
