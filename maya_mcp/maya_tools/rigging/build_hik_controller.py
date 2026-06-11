#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 根据当前 FBX/UE 骨架创建 HumanIK 控制器


def build_hik_controller(character_name: str = "Character1") -> dict:
    """根据当前 Maya 场景中的 FBX/UE 骨架创建 HumanIK 控制器。

    该工具会调用工具目录内置的 FbxToHIK 流程：加载 HumanIK，创建 Character，
    自动映射 UE 命名骨骼、脊柱、颈部、手指、twist/roll 骨骼，并创建 HIK Control Rig。

    Args:
        character_name: HIK Character 节点名称，默认 "Character1"。

    Returns:
        dict: success / message / created_summary / traceback。

    示例调用:
        build_hik_controller()
        build_hik_controller(character_name="QinQiong_HIK")
    """
    import os
    import sys
    import importlib.util
    import traceback

    def _load_core():
        for root in sys.path:
            if not root:
                continue
            candidate = os.path.join(root, "maya_mcp", "maya_tools", "rigging", "__fbx_to_hik_core.py")
            if os.path.isfile(candidate):
                spec = importlib.util.spec_from_file_location("rigging_mcp_fbx_to_hik_core", candidate)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.FbxToHIK
        raise RuntimeError("未在 MCP 工具目录中找到 __fbx_to_hik_core.py")

    try:
        import maya.cmds as cmds
        import maya.mel as mel

        FbxToHIK = _load_core()
        builder = FbxToHIK(character_name=character_name or "Character1")
        builder.build()

        try:
            characters = mel.eval("hikGetSceneCharacters()") or []
        except Exception:
            characters = []

        created_summary = {
            "character_name": builder.character_name,
            "character_exists": cmds.objExists(builder.character_name),
            "scene_characters": characters,
        }
        return {
            "success": True,
            "message": "HumanIK 控制器创建完成。",
            "created_summary": created_summary,
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "success": False,
            "message": f"创建 HIK 控制器失败: {str(e)}",
            "traceback": traceback.format_exc(),
        }
