#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 设置播放时间范围


def set_time_range(start: float, end: float, current: float = -1) -> dict:
    """设置场景的播放时间范围（动画帧范围）。

    Args:
        start: 起始帧。
        end: 结束帧。
        current: 设置当前帧，小于 0 表示不修改。默认 -1。

    Returns:
        dict: success / start / end / current / message。

    示例调用:
        set_time_range(start=1, end=120)
        set_time_range(start=0, end=240, current=0)
    """
    import maya.cmds as cmds
    import traceback

    try:
        cmds.playbackOptions(minTime=start, maxTime=end,
                             animationStartTime=start, animationEndTime=end)
        if current >= 0:
            cmds.currentTime(current)
        cur = cmds.currentTime(query=True)
        return {"success": True, "start": start, "end": end, "current": float(cur),
                "message": f"时间范围已设为 {start}-{end}，当前帧 {cur}。"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"设置时间范围失败: {str(e)}", "traceback": traceback.format_exc()}
