# MayaMCP

通过 [Model Context Protocol（MCP）](https://modelcontextprotocol.io/) 让 AI 客户端调用 Autodesk Maya 工具。

MayaMCP 将 MCP 客户端、运行在外部 Python 环境中的 MCP Server，以及 Maya 内部的 Socket 监听器连接起来。AI 发起工具调用后，MCP Server 会把调用脚本发送到 Maya，并在 Maya 主线程执行，从而安全地使用 `maya.cmds` 完成场景、物体、材质、灯光和动画操作。

> 当前项目处于 Alpha 阶段。建议先在测试场景中验证工具行为，再用于正式工程。

## 功能概览

- 基于 MCP stdio 协议接入 Claude Desktop、Cursor 等 MCP 客户端。
- 通过本机 TCP 回环地址 `127.0.0.1:50011` 与 Maya 通信。
- 使用 `maya.utils.executeInMainThreadWithResult` 将脚本调度到 Maya 主线程执行。
- 自动扫描 `maya_mcp/maya_tools/`，将工具脚本注册为 MCP tools。
- 根据函数签名和类型注解自动生成 MCP 输入 Schema。
- 支持 Maya 顶部菜单启动、停止、重启和查看监听状态。
- 支持通过 `install.py` 将 Maya 菜单注册到 `userSetup.py`，实现 Maya 启动时自动加载。

## 工作原理

```text
┌──────────────────┐       stdio        ┌──────────────────┐
│ MCP 客户端       │ ◄────────────────► │ MayaMCP Server   │
│ Claude / Cursor  │                    │ 外部 Python      │
└──────────────────┘                    └────────┬─────────┘
                                                  │ TCP 127.0.0.1:50011
                                                  ▼
                                        ┌──────────────────┐
                                        │ Maya 监听器      │
                                        │ Maya 主线程执行  │
                                        └──────────────────┘
```

一次工具调用的执行流程：

1. MCP 客户端启动 `maya_mcp`，并通过 stdio 连接 MCP Server。
2. MCP Server 扫描 `maya_mcp/maya_tools/`，发现并注册可用工具。
3. MCP 客户端调用某个 Maya 工具。
4. MCP Server 读取对应工具脚本，将参数包装为可执行 Python 脚本。
5. Maya 监听器接收脚本，并通过 `executeInMainThreadWithResult` 调度到 Maya 主线程。
6. Maya 执行完成后返回 JSON 结果，MCP Server 再将结果返回给客户端。

## 环境要求

### MCP Server 端

- Python 3.10 或更高版本。
- 可安装以下 Python 依赖：
  - `mcp>=1.0.0`
  - `pydantic>=2.0.0`
  - `pydantic-core>=2.0.0`

### Maya 端

- Autodesk Maya。
- 能够在 Maya Script Editor 的 Python 标签中执行 Python 脚本。
- Maya 与 MCP Server 运行在同一台机器上，或能够访问 MCP Server 配置的监听地址。

默认仅监听 `127.0.0.1`，不会对局域网开放。

## 安装

先将仓库克隆到本地，并进入仓库目录：

```bash
git clone https://github.com/Matoba-Seiji/MayaMCP.git
cd MayaMCP
```

建议使用虚拟环境安装 MCP Server 依赖：

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

如果不需要可编辑安装，也可以只安装依赖：

```bash
python -m pip install "mcp>=1.0.0" "pydantic>=2.0.0" "pydantic-core>=2.0.0"
```

## 启动 Maya 监听器

MCP Server 启动前，必须先让 Maya 监听 `127.0.0.1:50011`。

### 方式一：通过 Script Editor 启动

1. 打开 Maya。
2. 打开 **Script Editor**，切换到 **Python** 标签。
3. 执行下面的代码，将路径替换为本地仓库的实际路径：

```python
exec(open(
    r"C:/path/to/MayaMCP/startup_mcp_listener.py",
    encoding="utf-8"
).read())
```

看到类似下面的输出，表示监听器已启动：

```text
[MayaMCP] Socket Server 已启动，监听 127.0.0.1:50011
```

停止监听：

```python
stop_mcp_server()
```

### 方式二：通过 Maya 顶部菜单管理

运行安装器，将 MayaMCP 菜单注册到 Maya 的 `userSetup.py`：

```bash
python install.py
```

安装器会尝试写入：

- 通用路径：`<Maya 用户目录>/scripts/userSetup.py`
- 已存在的 Maya 版本目录下的 `scripts/userSetup.py`

重启 Maya 后，顶部会出现 **Maya MCP** 菜单，可执行：

- 启动监听
- 停止监听
- 重启监听
- 查看监听状态

卸载菜单启动块：

```bash
python install.py --uninstall
```

> `install.py` 会把当前仓库的绝对路径写入 `userSetup.py`。如果仓库移动到了其他位置，请重新执行安装；如果不再使用本项目，建议执行卸载命令。

## 配置 MCP 客户端

在 MCP 客户端配置文件的 `mcpServers` 中加入：

```json
{
  "mcpServers": {
    "maya-mcp": {
      "command": "C:/path/to/MayaMCP/.venv/Scripts/python.exe",
      "args": ["-m", "maya_mcp"],
      "cwd": "C:/path/to/MayaMCP"
    }
  }
}
```

### Windows 路径示例

```json
{
  "mcpServers": {
    "maya-mcp": {
      "command": "C:/Users/your-name/Documents/GitHub/MayaMCP/.venv/Scripts/python.exe",
      "args": ["-m", "maya_mcp"],
      "cwd": "C:/Users/your-name/Documents/GitHub/MayaMCP"
    }
  }
}
```

如果使用的是系统 Python，也可以将 `command` 设置为 `python`，但必须确保该 Python 环境已经安装项目依赖。

配置完成后，重启 MCP 客户端，并确认：

1. Maya 监听器已经启动。
2. MCP 客户端显示 `maya-mcp` 已连接。
3. 客户端能够获取到 Maya 工具列表。

## 当前工具

工具会按目录自动发现，工具名与 Python 文件名一致。

### 场景操作

| 工具 | 作用 |
| --- | --- |
| `new_scene` | 新建场景 |
| `open_scene` | 打开 Maya 场景文件 |
| `save_scene` | 保存当前场景或另存为指定路径 |
| `import_file` | 导入文件 |
| `export_file` | 导出文件 |
| `list_objects` | 查询场景中的对象 |
| `get_scene_info` | 获取场景信息 |

### 物体操作

| 工具 | 作用 |
| --- | --- |
| `create_object` | 创建基础几何体 |
| `delete_object` | 删除对象 |
| `select_objects` | 选择或清除选择对象 |
| `rename_object` | 重命名对象 |
| `set_object_transform` | 设置平移、旋转和缩放 |
| `set_object_property` | 设置对象属性 |
| `get_object_properties` | 获取对象属性 |

### 材质与灯光

| 工具 | 作用 |
| --- | --- |
| `create_material` | 创建材质 |
| `assign_material` | 为对象分配材质 |
| `create_light` | 创建灯光 |

### 动画

| 工具 | 作用 |
| --- | --- |
| `set_keyframe` | 设置关键帧 |
| `set_time_range` | 设置播放范围和当前帧 |

### Maya 工具

| 工具 | 作用 |
| --- | --- |
| `get_maya_version` | 获取 Maya 版本 |
| `execute_python_script` | 执行 Python 脚本 |
| `execute_mel_script` | 执行 MEL 脚本 |

> `execute_python_script` 和 `execute_mel_script` 可以执行任意传入脚本。请只在可信的 MCP 客户端和可信的对话环境中启用，并在执行删除、覆盖、导出等操作前确认目标路径和场景状态。

## 使用示例

连接成功后，可以通过自然语言调用工具，例如：

```text
在原点创建一个半径为 2 的球体，并命名为 hero_ball。
```

```text
获取当前场景中的所有 mesh 对象，并返回它们的名称和基本属性。
```

```text
将 pCube1 的动画范围设置为 1 到 120，并在第 1 帧和第 24 帧为 translateX 设置关键帧。
```

```text
创建一个红色 Blinn 材质并分配给 pCube1。
```

## 添加自定义工具

在 `maya_mcp/maya_tools/<domain>/` 下新建 Python 文件，并定义一个与文件名相同的函数。例如，新建 `maya_mcp/maya_tools/object/freeze_transforms.py`：

```python
def freeze_transforms(object_names: str = "") -> dict:
    """冻结指定对象的变换。

    Args:
        object_names: 以逗号分隔的对象名称。为空时使用当前选择。

    Returns:
        dict: 包含 success 和 message 的 JSON 可序列化结果。
    """
    import maya.cmds as cmds

    names = [name.strip() for name in object_names.split(",") if name.strip()]
    if not names:
        names = cmds.ls(selection=True, long=True) or []

    if not names:
        return {"success": False, "message": "没有可处理的对象"}

    cmds.makeIdentity(names, apply=True, translate=True, rotate=True, scale=True)
    return {
        "success": True,
        "message": f"已冻结 {len(names)} 个对象的变换",
        "objects": names,
    }
```

添加工具时请遵循：

- 文件名必须与工具函数名一致。
- 函数需要有类型注解，类型注解会用于生成 MCP 输入 Schema。
- 函数的 docstring 会作为 MCP 工具描述提供给 AI。
- `maya.cmds`、`maya.mel` 等 Maya 专用模块必须放在函数体内导入，因为 MCP Server 端扫描工具时没有 Maya Python 环境。
- 返回值应为可 JSON 序列化的数据，建议统一返回包含 `success` 和 `message` 的字典。
- 添加工具后重启 MCP Server，使工具重新扫描注册。

## 配置端口

默认配置为：

```text
Host: 127.0.0.1
Port: 50011
```

如需修改端口，必须同时修改：

- `maya_mcp/server.py` 中的 `MAYA_HOST` / `MAYA_PORT`
- `maya_mcp/connector/maya_server_listener.py` 中的 `HOST` / `PORT`

修改后需要重启 Maya 监听器和 MCP Server。

## 日志与故障排查

MCP Server 日志默认写入系统临时目录中的 `MayaMCPServer.log`，仓库内的 `MayaMCPServer.log` 也可能作为本地调试日志保留。

### MCP 客户端无法连接

检查：

1. `command` 是否指向安装了项目依赖的 Python。
2. `cwd` 是否指向仓库根目录。
3. MCP 客户端配置 JSON 是否有效。
4. MCP 客户端重启后是否重新加载了配置。

### 工具列表为空

检查：

1. `maya_mcp/maya_tools/` 下的脚本是否存在。
2. 文件名和函数名是否一致。
3. 工具脚本在没有 Maya 环境的情况下是否可以被扫描。
4. 工具函数的参数是否包含有效类型注解。
5. MCP Server 日志中是否存在工具预加载错误。

### 工具调用失败或连接超时

检查：

1. Maya 监听器是否已启动。
2. Maya 是否仍在监听 `127.0.0.1:50011`。
3. Maya 与 MCP Server 的端口配置是否一致。
4. Maya 是否处于阻塞状态或正在执行长时间操作。
5. 工具脚本是否调用了当前 Maya 版本不支持的 API。

### 端口被占用

关闭其他占用 `50011` 端口的服务，或按照上面的说明修改两端端口配置，然后重新启动监听器。

## 项目结构

```text
MayaMCP/
├── maya_mcp/
│   ├── server.py                    # MCP Server 核心与工具调用分发
│   ├── OperationManager.py          # 工具扫描、Schema 生成和注册
│   ├── connector/
│   │   ├── maya_connection.py      # 外部 Python 到 Maya 的 Socket 客户端
│   │   └── maya_server_listener.py  # Maya 内部 Socket 服务端
│   ├── maya_tools/                  # 按领域组织的 Maya 工具
│   │   ├── animation/
│   │   ├── light/
│   │   ├── material/
│   │   ├── object/
│   │   ├── scene/
│   │   └── utils/
│   └── ui/
│       ├── menu.py                  # Maya MCP 顶部菜单
│       └── service.py               # 监听服务控制
├── startup_mcp_listener.py          # 在 Maya 中启动监听器
├── install.py                       # 安装/卸载 Maya 启动菜单
├── pyproject.toml                   # Python 包和依赖配置
└── README.md
```

## 开发检查

提交前建议至少执行：

```bash
python -m compileall maya_mcp startup_mcp_listener.py install.py
```

如果本地已经安装依赖，可以进一步检查 MCP Server 是否能够启动到工具发现阶段：

```bash
python -m maya_mcp
```

该命令会等待 MCP 客户端通过 stdio 连接；不要在普通终端中长时间运行，验证完成后使用 `Ctrl+C` 结束。

## 许可证

项目元数据当前声明采用 MIT License。正式发布前，请在仓库根目录补充完整的 `LICENSE` 文件。
