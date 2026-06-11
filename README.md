# Maya MCP

通过 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 远程控制 Autodesk Maya。
通过 socket 将 MCP 工具调用转发到 Maya，
主线程调度使用 Maya 自带的 `maya.utils.executeInMainThreadWithResult`。

## 架构

```
┌─────────────┐   stdio    ┌──────────────┐   socket(50011)   ┌─────────────────────┐
│  MCP 客户端 │ ─────────► │  MCP Server  │ ────────────────► │  Maya 内监听器      │
│ (Claude等)  │ ◄───────── │ (maya_mcp)   │ ◄──────────────── │ (主线程执行脚本)    │
└─────────────┘            └──────────────┘                   └─────────────────────┘
```

- **MCP Server**：扫描 `maya_mcp/maya_tools/` 下每个 `.py`，把与文件同名的函数注册为 MCP 工具。
  工具被调用时，把函数源码包装成脚本，通过 socket 发给 Maya 执行并取回 JSON 结果。
- **Connector**：socket 通信层，协议为 `[4字节大端长度头] + [UTF-8 正文]`。
- **Maya 监听器**：在 Maya 里跑后台 socket server，收到脚本后用
  `executeInMainThreadWithResult` 调度到主线程执行（保证 `maya.cmds` 可用）。

## 目录结构

```
MayaMCP/
├── maya_mcp/
│   ├── __init__.py / __main__.py / log.py
│   ├── server.py                 # MCP Server 核心
│   ├── OperationManager.py        # 工具扫描/注册
│   ├── connector/
│   │   ├── maya_connection.py     # PC 端 socket 客户端
│   │   └── maya_server_listener.py# Maya 内 socket 服务端
│   └── maya_tools/                # 所有工具（按域分目录）
│       ├── scene/   get_scene_info, new_scene, open_scene, save_scene, import_file, export_file, list_objects
│       ├── object/  create_object, delete_object, select_objects, rename_object,
│       │            set_object_transform, set_object_property, get_object_properties
│       ├── material/ create_material, assign_material
│       ├── light/   create_light
│       ├── animation/ set_keyframe, set_time_range
│       └── utils/   execute_python_script, execute_mel_script, get_maya_version
├── startup_mcp_listener.py        # Maya 端启动脚本
├── pyproject.toml
└── README.md
```

## 安装

PC 端（运行 MCP Server 的 Python 环境，需 3.10+）：

```bash
cd MayaMCP
pip install -e .
# 或仅安装依赖
pip install "mcp>=1.0.0" "pydantic>=2.0.0"
```

## 使用步骤

### 1. 在 Maya 中启动监听器

打开 Maya，在 Script Editor 的 **Python** 标签中执行：

```python
exec(open(r"C:/Users/yanchaofeng/Desktop/MayaMCP/startup_mcp_listener.py", encoding="utf-8").read())
```

看到 `[MayaMCP] Socket Server 已启动，监听 127.0.0.1:50011` 即成功。

> 如需 Maya 启动时自动监听，把上面这行加入 `userSetup.py`。
> 停止监听：在 Script Editor 执行 `stop_mcp_server()`。

### 2. 配置 MCP 客户端

在客户端（如 Claude Desktop）的 MCP 配置中加入：

```json
{
  "mcpServers": {
    "maya-mcp": {
      "command": "python",
      "args": ["-m", "maya_mcp"],
      "cwd": "C:/Users/yanchaofeng/Desktop/MayaMCP"
    }
  }
}
```

### 3. 开始使用

连接后即可让 AI 调用工具，例如：

- “在原点创建一个半径为 2 的球体” → `create_object`
- “给 pCube1 指定一个红色 blinn 材质” → `create_material` + `assign_material`
- “把动画范围设为 1-120，并在第 1、24 帧给 pCube1 的 translateX 打关键帧” → `set_time_range` + `set_keyframe`

## 扩展工具

在 `maya_mcp/maya_tools/<域>/` 下新建 `your_tool.py`，写一个与文件同名的函数：

```python
def your_tool(arg1: str, arg2: int = 0) -> dict:
    """工具说明（这段 docstring 会作为工具描述提供给 AI）。

    Args:
        arg1: ...
        arg2: ...

    Returns:
        dict: success / ... / message
    """
    import maya.cmds as cmds
    # 在这里写逻辑，返回可 JSON 序列化的 dict
    return {"success": True, "message": "done"}
```

要点：
- 函数名必须与文件名一致。
- 所有 `import`（含 `maya.cmds`）放在函数体内，因为 Server 端预加载时没有 Maya 环境。
- 参数类型注解会自动生成 JSON Schema；返回值建议统一为含 `success`/`message` 的 dict。

## 端口

默认 `127.0.0.1:50011`。如需修改，同时改：
- `maya_mcp/server.py` 的 `MAYA_PORT`
- `maya_mcp/connector/maya_server_listener.py` 的 `PORT`
