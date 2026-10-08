# MayaMCP

通过 MCP 在 Codex 等客户端中操作 Autodesk Maya。支持读取场景、创建和修改对象、设置材质与动画，以及执行 Python 或 MEL 脚本。

## 安装

需要 Python 3.10 或更新版本。以下以 Windows 为例，在仓库目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe install.py
```

重启 Maya，在顶部 **Maya MCP → 启动监听**。用 **查看监听状态** 确认监听器已启动。安装器通过 Maya 的 `userSetup.py` 加载菜单；移动仓库后需重新运行 `install.py`。

## 配置 Codex

在 `~/.codex/config.toml` 中加入以下配置，将两处路径改为本仓库的绝对路径：

```toml
[mcp_servers."maya-mcp"]
command = "C:/你的路径/MayaMCP/.venv/Scripts/python.exe"
args = ["-m", "maya_mcp"]
cwd = "C:/你的路径/MayaMCP"
enabled = true
```

重新打开 Codex 聊天，让 MCP 工具加载。Maya 监听器默认使用本机端口 `50011`；[3dsMaxMCP](https://github.com/Matoba-Seiji/3dsMaxMCP) 使用 `50012`。

## 常见问题

- **连接失败：**确认 Maya 正在运行，且菜单的 **查看监听状态** 显示“监听中”；检查端口 `50011` 是否被其他程序占用。
- **没有顶部菜单：**重新运行 `install.py` 并重启 Maya。
- **卸载菜单：**运行 `.\.venv\Scripts\python.exe install.py --uninstall`。

项目元数据标注 MIT 许可，目前仓库尚未附 `LICENSE` 文件。
