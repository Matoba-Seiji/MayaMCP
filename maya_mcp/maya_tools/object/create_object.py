#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 在 Maya 中创建基础几何体


def create_object(object_type: str, name: str = "", position: str = "0,0,0", params: str = "") -> dict:
    """在 Maya 场景中创建一个基础几何体对象。

    支持的 object_type（不区分大小写）:
    - cube/box: polyCube，参数 width/height/depth/subdivisionsX/subdivisionsY/subdivisionsZ
    - sphere: polySphere，参数 radius/subdivisionsX/subdivisionsY
    - cylinder: polyCylinder，参数 radius/height/subdivisionsX/subdivisionsY/subdivisionsZ
    - cone: polyCone，参数 radius/height/subdivisionsX/subdivisionsY
    - plane: polyPlane，参数 width/height/subdivisionsX/subdivisionsY
    - torus: polyTorus，参数 radius/sectionRadius/subdivisionsX/subdivisionsY
    - pyramid: polyPyramid，参数 sideLength
    - disc/pipe/prism/helix/gear/platonicSolid: 对应 poly* 命令

    Args:
        object_type: 几何体类型，如 "cube"、"sphere"、"cylinder"。
        name: 对象名称。为空则使用 Maya 默认命名。
        position: 世界坐标位置 "x,y,z"，默认 "0,0,0"。
        params: 创建参数 JSON 字符串，如 '{"radius": 2, "subdivisionsX": 32}'。为空使用默认参数。

    Returns:
        dict: success / name / object_type / position / applied_params / message。

    示例调用:
        create_object(object_type="sphere")
        create_object(object_type="cube", name="myBox", position="5,0,0", params='{"width": 2, "height": 4}')
    """
    import maya.cmds as cmds
    import json
    import traceback

    try:
        try:
            pos_parts = [float(p.strip()) for p in position.split(",")]
            if len(pos_parts) != 3:
                return {"success": False, "message": f"位置参数需要 3 个数值(x,y,z)，实际 {len(pos_parts)} 个。"}
        except ValueError:
            return {"success": False, "message": f"位置参数 '{position}' 含无效数值，请用 'x,y,z' 格式。"}

        create_params = {}
        if params and params.strip():
            try:
                create_params = json.loads(params)
            except json.JSONDecodeError as e:
                return {"success": False, "message": f"params JSON 解析失败: {str(e)}"}

        cmd_map = {
            "cube": cmds.polyCube, "box": cmds.polyCube,
            "sphere": cmds.polySphere,
            "cylinder": cmds.polyCylinder,
            "cone": cmds.polyCone,
            "plane": cmds.polyPlane,
            "torus": cmds.polyTorus,
            "pyramid": cmds.polyPyramid,
            "disc": cmds.polyDisc,
            "pipe": cmds.polyPipe,
            "prism": cmds.polyPrism,
            "helix": cmds.polyHelix,
            "gear": getattr(cmds, "polyGear", None),
            "platonicsolid": cmds.polyPlatonicSolid,
        }
        key = object_type.strip().lower()
        create_fn = cmd_map.get(key)
        if create_fn is None:
            return {"success": False, "message": f"不支持的 object_type '{object_type}'。"}

        kwargs = dict(create_params)
        if name and name.strip():
            kwargs["name"] = name.strip()

        result = create_fn(**kwargs)
        transform = result[0] if isinstance(result, (list, tuple)) else result

        cmds.move(pos_parts[0], pos_parts[1], pos_parts[2], transform, absolute=True)

        actual = cmds.xform(transform, query=True, worldSpace=True, translation=True)
        return {
            "success": True,
            "name": transform,
            "object_type": object_type,
            "position": [float(actual[0]), float(actual[1]), float(actual[2])],
            "applied_params": create_params,
            "message": f"已创建 {object_type} '{transform}'，位置 {actual}。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"创建对象失败: {str(e)}", "traceback": traceback.format_exc()}
