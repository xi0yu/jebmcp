# 🚀 JEBMCP: JEB & MCP Integration Hub

**JEBMCP** 将 **JEB 反编译能力** 与 **MCP (Minecraft Coder Pack)** 相结合，提供高效的分析和自动化能力。  
它通过 **JSON-RPC / SSE / stdio** 与 JEB 交互，并提供一套 Python 脚本，帮助你完成方法调用关系获取、类/方法重命名、代码分析等任务。

---

## 🌟 目录

1. [简介](#简介)  
2. [客户端兼容性](#客户端兼容性)  
3. [安装](#安装)  
4. [项目结构](#项目结构)  
5. [许可证](#许可证)  
6. [更多资源](#更多资源)

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
               "get_app_manifest",
               "get_method_callers",
               "get_class_decompiled_code",
               "get_method_decompiled_code",
               "ping",
               "get_method_overrides",
               "get_method_smali",
               "get_current_project_info"
            ]
         }
      }
   }
   ```

   - **Claude 参考** [自定义 mcp 配置教程](https://docs.anthropic.com/zh-CN/docs/claude-code/mcp)

2. 在 JEB 中配置 MCP 服务
   - 打开 JEB 客户端
   - 导航到 `工具` -> `脚本`
   - 加载 `MCP.py` 脚本

---

## 🛠️ 项目结构

### server.py
- **用途**：为 **Claude / Cursor / Trae** 等工具集成 MCP 提供服务端支持  
- **注意**：不是命令行工具，用户无需手动运行  

### MCP.py
- **用途**：通过 JEB 客户端脚本运行，调用 MCP 功能  
- **注意**：不支持直接命令行执行，需在 JEB 内部使用  

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
