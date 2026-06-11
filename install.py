#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rigging MCP 一键安装器。

把 "Rigging MCP" 顶栏菜单的启动代码写入 Maya 的 userSetup.py，
使 Maya 每次启动时自动注册菜单（菜单内可一键启停监听 / 打开控制面板）。

用法（用任意系统 Python 运行即可，无需 mayapy）:
    python install.py            # 安装
    python install.py --uninstall  # 卸载
"""

import os
import sys
import glob

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
MENU_FILE = os.path.join(PROJECT_ROOT, "maya_mcp", "ui", "menu.py").replace("\\", "/")

MARK_BEGIN = "# >>> MayaRiggingMCP MENU (auto-generated) >>>"
MARK_END = "# <<< MayaRiggingMCP MENU <<<"


def _boot_block():
    return f"""{MARK_BEGIN}
def _rigging_mcp_boot():
    import importlib.util, os
    menu_file = r"{MENU_FILE}"
    if not os.path.isfile(menu_file):
        print("[RiggingMCP] 菜单文件不存在:", menu_file)
        return
    try:
        spec = importlib.util.spec_from_file_location("rigging_mcp_menu_boot", menu_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.create_menu()
        print("[RiggingMCP] 菜单已加载")
    except Exception as _e:
        print("[RiggingMCP] 菜单加载失败:", _e)
try:
    import maya.utils as _mu
    _mu.executeDeferred(_rigging_mcp_boot)
except Exception as _e:
    print("[RiggingMCP] 启动失败:", _e)
{MARK_END}
"""


def _maya_app_dir():
    """定位 Maya 用户目录（MAYA_APP_DIR 优先，否则 ~/Documents/maya）。"""
    env = os.environ.get("MAYA_APP_DIR")
    if env and os.path.isdir(env):
        return env
    candidates = [
        os.path.join(os.path.expanduser("~"), "Documents", "maya"),
        os.path.join(os.path.expanduser("~"), "maya"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]


def _usersetup_paths(app_dir):
    """返回要写入的 userSetup.py 路径列表。

    优先使用版本无关的 `<maya>/scripts/userSetup.py`（对所有版本生效）。
    若不存在则也覆盖各版本目录，确保至少命中用户当前版本。
    """
    paths = []
    generic = os.path.join(app_dir, "scripts")
    paths.append(os.path.join(generic, "userSetup.py"))
    for ver_dir in glob.glob(os.path.join(app_dir, "20*")):
        scripts = os.path.join(ver_dir, "scripts")
        if os.path.isdir(scripts):
            paths.append(os.path.join(scripts, "userSetup.py"))
    return paths


def _strip_block(text):
    """移除已存在的自动生成块。"""
    if MARK_BEGIN not in text:
        return text, False
    before = text.split(MARK_BEGIN)[0]
    after = text.split(MARK_END)[-1] if MARK_END in text else ""
    new = before.rstrip() + ("\n" + after.lstrip() if after.strip() else "\n")
    return new, True


def install():
    app_dir = _maya_app_dir()
    targets = _usersetup_paths(app_dir)
    written = []
    for path in targets:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = ""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        text, _ = _strip_block(text)
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + _boot_block()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        written.append(path)

    print("[安装完成] 已写入以下 userSetup.py:")
    for p in written:
        print("  -", p)
    print("\n重启 Maya 后，顶部会出现 “Rigging MCP” 菜单。")
    _print_mcp_config()


def uninstall():
    app_dir = _maya_app_dir()
    targets = _usersetup_paths(app_dir)
    cleaned = []
    for path in targets:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        new, found = _strip_block(text)
        if found:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            cleaned.append(path)
    if cleaned:
        print("[卸载完成] 已从以下文件移除菜单启动块:")
        for p in cleaned:
            print("  -", p)
    else:
        print("[卸载] 未发现已安装的菜单启动块。")


def _print_mcp_config():
    print("\n将以下配置加入 MCP 客户端 (mcp.json) 即可让 AI 调用工具:")
    print("-" * 60)
    print(f'''  "rigging-maya-mcp": {{
      "command": "python",
      "args": ["-m", "maya_mcp"],
      "cwd": "{PROJECT_ROOT}"
  }}''')
    print("-" * 60)


def main():
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
