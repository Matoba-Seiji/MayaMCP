#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Install the MayaMCP menu into Maya's userSetup.py."""

import glob
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
MENU_FILE = os.path.join(PROJECT_ROOT, "maya_mcp", "ui", "menu.py").replace("\\", "/")

MARK_BEGIN = "# >>> MayaMCP MENU (auto-generated) >>>"
MARK_END = "# <<< MayaMCP MENU <<<"


def _boot_block():
    return f"""{MARK_BEGIN}
def _maya_mcp_boot():
    import importlib.util, os
    menu_file = r"{MENU_FILE}"
    if not os.path.isfile(menu_file):
        print("[MayaMCP] 菜单文件不存在:", menu_file)
        return
    try:
        spec = importlib.util.spec_from_file_location("maya_mcp_menu_boot", menu_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.create_menu()
        print("[MayaMCP] 菜单已加载")
    except Exception as _e:
        print("[MayaMCP] 菜单加载失败:", _e)
try:
    import maya.utils as _mu
    _mu.executeDeferred(_maya_mcp_boot)
except Exception as _e:
    print("[MayaMCP] 启动失败:", _e)
{MARK_END}
"""


def _maya_app_dir():
    """Locate Maya's user directory."""
    env = os.environ.get("MAYA_APP_DIR")
    if env and os.path.isdir(env):
        return env

    candidates = [
        os.path.join(os.path.expanduser("~"), "Documents", "maya"),
        os.path.join(os.path.expanduser("~"), "maya"),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return candidates[0]


def _usersetup_paths(app_dir):
    """Return generic, versioned, and localized Maya userSetup.py paths."""
    paths = [os.path.join(app_dir, "scripts", "userSetup.py")]

    for version_dir in glob.glob(os.path.join(app_dir, "20*")):
        paths.append(os.path.join(version_dir, "scripts", "userSetup.py"))
        for locale_dir in glob.glob(os.path.join(version_dir, "*")):
            if not os.path.isdir(locale_dir):
                continue
            locale_scripts = os.path.join(locale_dir, "scripts")
            if os.path.isdir(locale_scripts) or os.path.basename(locale_dir).lower() not in {"prefs", "scripts"}:
                paths.append(os.path.join(locale_scripts, "userSetup.py"))

    return list(dict.fromkeys(paths))


def _strip_block(text):
    """Remove a previously installed MayaMCP block."""
    if MARK_BEGIN not in text:
        return text, False

    before = text.split(MARK_BEGIN, 1)[0]
    after = text.split(MARK_END, 1)[-1] if MARK_END in text else ""
    new = before.rstrip() + ("\n" + after.lstrip() if after.strip() else "\n")
    return new, True


def install():
    app_dir = _maya_app_dir()
    written = []

    for path in _usersetup_paths(app_dir):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = ""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as stream:
                text = stream.read()

        text, _ = _strip_block(text)
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n" + _boot_block()

        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)
        written.append(path)

    print("[安装完成] 已写入以下 userSetup.py:")
    for path in written:
        print("  -", path)
    print("\n重启 Maya 后，顶部会出现 “Maya MCP” 菜单。")
    _print_mcp_config()


def uninstall():
    app_dir = _maya_app_dir()
    cleaned = []

    for path in _usersetup_paths(app_dir):
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as stream:
            text = stream.read()
        new, found = _strip_block(text)
        if found:
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(new)
            cleaned.append(path)

    if cleaned:
        print("[卸载完成] 已从以下文件移除菜单启动块:")
        for path in cleaned:
            print("  -", path)
    else:
        print("[卸载] 未发现已安装的菜单启动块。")


def _print_mcp_config():
    print("\n将以下配置加入 MCP 客户端 (mcp.json) 即可让 AI 调用工具:")
    print("-" * 60)
    print(f'''  "maya-mcp": {{
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
