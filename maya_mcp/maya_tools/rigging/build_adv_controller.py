#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 根据当前 FBX/UE 骨架创建 AdvancedSkeleton 控制器


def build_adv_controller(fit_file: str = "", generate_root: bool = False) -> dict:
    """根据当前 Maya 场景中的 FBX/UE 骨架创建 AdvancedSkeleton 控制器。

    该工具会调用工具目录内置的 FbxToADV 流程：自动查找 AdvancedSkeleton，
    导入/对齐 FitSkeleton，执行 ReBuildAdvancedSkeleton，并用 ADV 骨骼约束原 FBX 骨骼。

    Args:
        fit_file: 可选，指定 ADV FitSkeleton 文件路径；为空则自动使用 AdvancedSkeleton 自带 biped.ma。
        generate_root: 是否在原 FBX pelvis 上方创建 root 根骨骼，默认 False。

    Returns:
        dict: success / message / created_summary / traceback。

    示例调用:
        build_adv_controller()
        build_adv_controller(generate_root=True)  # 如需额外创建 root 根骨骼
    """
    import os
    import sys
    import importlib.util
    import traceback

    def _load_core():
        for root in sys.path:
            if not root:
                continue
            candidate = os.path.join(root, "maya_mcp", "maya_tools", "rigging", "__fbx_to_adv_core.py")
            if os.path.isfile(candidate):
                spec = importlib.util.spec_from_file_location("rigging_mcp_fbx_to_adv_core", candidate)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.FbxToADV
        raise RuntimeError("未在 MCP 工具目录中找到 __fbx_to_adv_core.py")

    try:
        import maya.cmds as cmds

        FbxToADV = _load_core()
        builder = FbxToADV(fit_file=fit_file or None)
        builder.build(generate_root=bool(generate_root))

        created_summary = {
            "deformation_system": cmds.objExists("DeformationSystem"),
            "motion_system": cmds.objExists("MotionSystem"),
            "fit_skeleton": cmds.objExists("FitSkeleton"),
            "root_exists": cmds.objExists("root"),
            "control_set": cmds.objExists("ControlSet"),
        }
        return {
            "success": True,
            "message": "AdvancedSkeleton 控制器创建完成。",
            "created_summary": created_summary,
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "success": False,
            "message": f"创建 ADV 控制器失败: {str(e)}",
            "traceback": traceback.format_exc(),
        }
