#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 获取 Maya 当前场景的综合信息


def get_scene_info() -> dict:
    """获取当前 Maya 场景的综合信息。

    返回文件路径、对象统计、时间范围、单位设置等。

    Returns:
        dict: 操作结果。
            - success (bool): 是否成功。
            - file_path (str): 当前场景文件完整路径（未保存时为空）。
            - file_name (str): 场景文件名。
            - is_saved (bool): 场景是否已保存到文件。
            - object_counts (dict): 各类型对象数量统计 total/meshes/lights/cameras/joints/transforms。
            - time_range (dict): start/end/current/fps。
            - units (dict): linear/angle/time。
            - message (str): 描述信息。

    示例调用:
        get_scene_info()
    """
    import maya.cmds as cmds
    import os
    import traceback

    try:
        file_path = cmds.file(query=True, sceneName=True) or ""
        file_name = os.path.basename(file_path) if file_path else ""
        is_saved = bool(file_path)

        meshes = cmds.ls(type="mesh", long=True) or []
        lights = cmds.ls(lights=True, long=True) or []
        cameras = cmds.ls(type="camera", long=True) or []
        joints = cmds.ls(type="joint", long=True) or []
        transforms = cmds.ls(type="transform", long=True) or []
        all_dag = cmds.ls(dag=True, long=True) or []

        object_counts = {
            "total": len(all_dag),
            "meshes": len(meshes),
            "lights": len(lights),
            "cameras": len(cameras),
            "joints": len(joints),
            "transforms": len(transforms),
        }

        start = cmds.playbackOptions(query=True, minTime=True)
        end = cmds.playbackOptions(query=True, maxTime=True)
        current = cmds.currentTime(query=True)
        fps_map = {
            "game": 15.0, "film": 24.0, "pal": 25.0, "ntsc": 30.0,
            "show": 48.0, "palf": 50.0, "ntscf": 60.0,
        }
        time_unit = cmds.currentUnit(query=True, time=True)
        fps = fps_map.get(time_unit, 24.0)

        time_range = {
            "start": float(start),
            "end": float(end),
            "current": float(current),
            "fps": fps,
        }

        units = {
            "linear": cmds.currentUnit(query=True, linear=True),
            "angle": cmds.currentUnit(query=True, angle=True),
            "time": time_unit,
        }

        return {
            "success": True,
            "file_path": file_path,
            "file_name": file_name,
            "is_saved": is_saved,
            "object_counts": object_counts,
            "time_range": time_range,
            "units": units,
            "message": f"场景: {file_name if file_name else '未保存'}，"
                       f"共 {object_counts['total']} 个 DAG 节点（网格 {object_counts['meshes']}, "
                       f"灯光 {object_counts['lights']}, 相机 {object_counts['cameras']}, 关节 {object_counts['joints']}），"
                       f"帧范围: {start}-{end}，当前帧: {current}，帧率: {fps} FPS。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"获取场景信息失败: {str(e)}", "traceback": traceback.format_exc()}
