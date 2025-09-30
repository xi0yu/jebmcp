# 🚀 JEBMCP: JEB & MCP

**JEBMCP** 将 **JEB 反编译能力** 与 **MCP (Model Context Protocol)** 相结合，提供高效的分析和自动化能力。  
它通过 **JSON-RPC / SSE / stdio** 与 JEB 交互，并提供一套 Python 脚本，帮助你完成方法调用关系获取、类/方法重命名、代码分析等任务。

---

## 🌟 目录

1. [简介](#简介)  
2. [客户端兼容性](#客户端兼容性)  
3. [安装](#安装)  
4. [使用方法](#使用方法)  
5. [项目结构](#项目结构)  
6. [批量重命名工具](#批量重命名工具)  
7. [许可证](#许可证)  
8. [更多资源](#更多资源)

---

## 🧐 简介

JEBMCP 主要特性：  
- 集成 JEB 与 MCP，支持项目分析与操作  
- 提供 Python 工具接口，便于自动化调用  
- 支持多种交互方式（JSON-RPC / SSE / stdio）  
- 支持方法/类重命名、调用关系追踪、反编译结果获取等功能  

---

## 💻 客户端兼容性

不同客户端对交互方式的支持情况：  

- **Claude / Claude code**  
  - 支持 SSE  
  - 支持 HTTP  
  - 支持 stdio  

- **Trae / Cursor / Vscode**  
  - 支持 stdio  

提示：  
- 使用 **Cursor / Trae / Vscode** 时，请确保 MCP 服务通过 `stdio` 模式运行。  
- 使用 **Claude / Claude code** 时，可以选择 `sse` 或 `http`，获得更灵活的交互方式。  

---

## ⚙️ 安装

1. 克隆仓库  
   ```bash
   git clone https://github.com/xi0yu/jebmcp.git
   ```

2. 进入项目目录  
   ```bash
   cd jebmcp
   ```

3. 安装依赖  
   确保已安装 Python 3.x，然后执行：  
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### 方式一：使用 NPM 包（推荐）

**JEBMCP** 已发布到 NPM 官网，可以直接使用 `npx` 执行，无需下载本地 `server.py`：

```json
{
   "mcpServers": {
      "jeb": {
         "command": "npx",
         "args": ["-y", "@xi0yu/jebmcp-proxy"]
      }
   }
}
```

### 方式二：本地运行

1. 配置 MCP 服务
   - **Claude / Cursor / Trae** 在 AI 配置中配置 mcpServers 
   ```json
   {
      "mcpServers": {
         "jeb": {
            "command": "python",
            "args": [
               "${JEB_MCP_PATH}/server.py"
            ],
            "autoApprove": [
               "ping", 
               "has_projects", 
               "get_projects", 
               "get_current_project_info",
               "get_app_manifest", 
               "get_class_decompiled_code", 
               "get_method_decompiled_code",
               "get_method_smali", 
               "get_class_methods", 
               "get_class_fields",
               "get_class_superclass", 
               "get_class_interfaces", 
               "get_class_type_tree",
               "get_method_callers", 
               "get_method_overrides", 
               "get_field_callers",
               "rename_batch_symbols"
            ]
         }
      }
   }
   ```

   - **Claude 参考** [自定义 mcp 配置教程](https://docs.anthropic.com/zh-CN/docs/claude-code/mcp)
   ```bash
   # 使用claude code参考如下方式
   claude mcp add jeb -- npx -y @xi0yu/jebmcp-proxy
   ```


2. 在 JEB 中配置 MCP 服务（两种方式都需要）
   - 打开 JEB 客户端
   - 导航到 `工具` -> `脚本`
   - 加载 `MCP.py` 脚本

**注意**：无论使用哪种方式，都需要下载本项目中的 `MCP.py` 等文件到本地，供 JEB 执行。NPM 包只是替代了 `server.py` 的运行方式。

---

## 🛠️ 项目结构

### server.py
- **用途**：为 **Claude / Cursor / Trae** 等工具集成 MCP 提供服务端支持  
- **注意**：不是命令行工具，用户无需手动运行  

### MCP.py
- **用途**：通过 JEB 客户端脚本运行，调用 MCP 功能  
- **注意**：不支持直接命令行执行，需在 JEB 内部使用  

---

## 🔄 批量重命名工具

新增的 `rename_batch_symbols` 工具支持批量重命名类、方法和字段。

### 数据结构

```json
[
    {
        "type": "class",
        "old_name": "wzp",
        "new_name": "ModuleInfoParser"
    },
    {
        "type": "method",
        "old_name": "wzp.a",
        "new_name": "getName"
    },
    {
        "type": "field",
        "old_name": "wzp.a",
        "new_name": "moduleName"
    }
]
```

### 字段说明

- `type`: 操作类型，可选值为 "class"、"method"、"field"
- `old_name`: 原始名称（完整路径）
  - class: "com.example.TestClass" 或 "wzp"
  - method: "com.example.TestClass.methodName" 或 "wzp.a"
  - field: "com.example.TestClass.fieldName" 或 "wzp.a"
- `new_name`: 新名称，支持两种格式：
  - 仅符号名称：如 "getName"、"moduleName"
  - 完整路径：如 "wzp.getName"、"wzp.moduleName"（系统会自动提取符号名称）

### 返回结果

```json
{
    "success": true,
    "summary": {
        "total": 3,
        "successful": 3,
        "failed": 0
    },
    "failed_operations": [],
    "message": "批量重命名完成: 总共 3 个操作，成功 3 个，失败 0 个"
}
```

### 使用示例

```python
# 批量重命名示例
rename_ops = [
    {
        "type": "class",
        "old_name": "wzp",
        "new_name": "ModuleInfoParser"
    },
    {
        "type": "method",
        "old_name": "wzp.a",
        "new_name": "getName"
    }
]

result = client.call("rename_batch_symbols", rename_ops)
```

---

## 📝 许可证

[![Stars](https://img.shields.io/github/stars/xi0yu/jebmcp?style=social)](https://github.com/xi0yu/jebmcp/stargazers)
[![Forks](https://img.shields.io/github/forks/xi0yu/jebmcp?style=social)](https://github.com/xi0yu/jebmcp/network/members)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=xi0yu/jebmcp&type=Date)](https://www.star-history.com/#xi0yu/jebmcp&Date)

---

## 🌍 更多资源

- [JEB 官方文档](https://www.pnfsoftware.com/jeb/apidoc)  
- [MCP 文档](https://mcp-docs.cn/introduction)  

感谢使用 JEBMCP，希望它能帮助你更高效地进行逆向工程任务！
