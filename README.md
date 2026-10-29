# MayaMCP

通过 MCP 在 Codex 等客户端中操作 Autodesk Maya。支持读取场景、创建和修改对象、设置材质与动画，以及执行 Python 或 MEL 脚本。

## 安装

需要 Python 3.10 或更新版本。以下以 Windows 为例，在仓库目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe install.py
```

重启 Maya，在顶部 **Maya MCP → 启动监听（实例1·50016）**。用 **查看监听状态** 确认监听器已启动。安装器通过 Maya 的 `userSetup.py` 加载菜单；移动仓库后需重新运行 `install.py`。

## 配置 Codex

在 `~/.codex/config.toml` 中加入以下配置，将两处路径改为本仓库的绝对路径：

```toml
[mcp_servers."maya-mcp"]
command = "C:/你的路径/MayaMCP/.venv/Scripts/python.exe"
args = ["-m", "maya_mcp", "--port", "50016"]
cwd = "C:/你的路径/MayaMCP"
enabled = true
```

重新打开 Codex 聊天，让 MCP 工具加载。Maya 监听器默认使用本机端口 `50016`；[3dsMaxMCP](https://github.com/Matoba-Seiji/3dsMaxMCP) 的默认端口是 `50012`（第二个 Max 实例为 `50013`）。

## 多实例（同时打开多个 Maya）

每个 Maya 进程各自运行监听器，用不同端口隔离；MCP 客户端按端口连接对应实例，互不影响：

1. 第一个 Maya：菜单 **Maya MCP → 启动监听（实例1 · 50016）**。
2. 第二个 Maya：菜单 **Maya MCP → 启动监听（实例2 · 50017）**。
3. 客户端为每个实例各配置一条 stdio 服务器，用 `--port` 指定端口（任何 MCP 客户端通用）：

```toml
[mcp_servers."maya-1"]
command = "python"
args = ["-m", "maya_mcp", "--port", "50016"]
cwd = "C:/你的路径/MayaMCP"

[mcp_servers."maya-2"]
command = "python"
args = ["-m", "maya_mcp", "--port", "50017"]
cwd = "C:/你的路径/MayaMCP"
```

也可以不传 `--port`，改用环境变量 `MAYAMCP_PORT=50017`（默认 `50016` 不变，旧配置无需修改）。两个实例的 Python 状态完全独立，调用只会发往对应端口的 Maya。

使用 `mcpServers` JSON 格式的客户端（Claude Desktop、Cursor 等）等价写法：

```json
{
  "mcpServers": {
    "maya-1": {
      "command": "python",
      "args": ["-m", "maya_mcp", "--port", "50016"],
      "cwd": "C:/你的路径/MayaMCP"
    },
    "maya-2": {
      "command": "python",
      "args": ["-m", "maya_mcp", "--port", "50017"],
      "cwd": "C:/你的路径/MayaMCP"
    }
  }
}
```

注意：端口 `50012` / `50013` 已分配给 3dsMaxMCP 的两个实例；Maya 两个实例使用 `50016` / `50017`（默认 `50016`），避免与 3dsMaxMCP 以及常见被占用端口（如 `50011`）冲突。菜单与 `maya_mcp` 代码更新后需要重启 Maya 才会重新加载。

## 常见问题

- **连接失败：**确认 Maya 正在运行，且菜单的 **查看监听状态** 显示“监听中”；检查端口 `50016` 是否被其他程序占用。
- **没有顶部菜单：**重新运行 `install.py` 并重启 Maya。
- **卸载菜单：**运行 `.\.venv\Scripts\python.exe install.py --uninstall`。

项目元数据标注 MIT 许可，目前仓库尚未附 `LICENSE` 文件。
