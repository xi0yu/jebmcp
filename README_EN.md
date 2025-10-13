# 🚀 JEBMCP: JEB & MCP

**JEBMCP** combines **JEB decompilation capabilities** with **MCP (Model Context Protocol)** to provide efficient analysis and automation capabilities.  
It interacts with JEB through **JSON-RPC / SSE / stdio** and provides a set of Python scripts to help you complete tasks such as method call relationship acquisition, class/method renaming, code analysis, etc.

---

## 🌟 Table of Contents

1. [Introduction](#introduction)  
2. [Client Compatibility](#client-compatibility)  
3. [Installation](#installation)  
4. [Usage](#usage)  
5. [Project Structure](#project-structure)  
6. [Batch Rename Tool](#batch-rename-tool)  
7. [License](#license)  
8. [More Resources](#more-resources)

---

## 🧐 Introduction

JEBMCP main features:  
- Integrates JEB with MCP, supports project analysis and operations  
- Provides Python tool interface for easy automation calls  
- Supports multiple interaction methods (JSON-RPC / SSE / stdio)  
- Supports method/class renaming, call relationship tracking, decompilation result acquisition, etc.  

---

## 💻 Client Compatibility

Support for different interaction methods by various clients:  

- **Claude / Claude code**  
  - Supports SSE  
  - Supports HTTP  
  - Supports stdio  

- **Trae / Cursor / Vscode**  
  - Supports stdio  

Tips:  
- When using **Cursor / Trae / Vscode**, please ensure the MCP service runs in `stdio` mode.  
- When using **Claude / Claude code**, you can choose `sse` or `http` for more flexible interaction.  

---

## ⚙️ Installation

1. Clone the repository  
   ```bash
   git clone https://github.com/xi0yu/jebmcp.git
   ```

2. Enter the project directory  
   ```bash
   cd jebmcp
   ```

3. Install dependencies  
   Make sure Python 3.x is installed, then execute:  
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Method 1: Using NPM Package (Recommended)

**JEBMCP** has been published to NPM, you can directly use `npx` to execute without downloading local `server.py`:

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

### Method 2: Local Execution

1. Configure MCP Service
   - **Claude / Cursor / Trae** configure mcpServers in AI settings 
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

   - **Claude Reference** [Custom MCP Configuration Tutorial](https://docs.anthropic.com/en/docs/claude-code/mcp)
   ```bash
   # Use claude code as follows
   claude mcp add jeb -- npx -y @xi0yu/jebmcp-proxy
   ```

2. Configure MCP Service in JEB (Required for both methods)
   - Open JEB client
   - Navigate to `Tools` -> `Scripts`
   - Load the `MCP.py` script

**Note**: Regardless of which method you use, you need to download the `MCP.py` and other files from this project locally for JEB execution. The NPM package only replaces the execution method of `server.py`.

---

## 🛠️ Project Structure

### server.py
- **Purpose**: Provides server-side support for **Claude / Cursor / Trae** and other tools to integrate MCP  
- **Note**: Not a command-line tool, users do not need to run it manually  

### MCP.py
- **Purpose**: Runs through JEB client scripts, calls MCP functionality  
- **Note**: Does not support direct command-line execution, needs to be used within JEB  

---

## 🔄 Batch Rename Tool

The new `rename_batch_symbols` tool supports batch renaming of classes, methods, and fields.

### Data Structure

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

### Field Description

- `type`: Operation type, can be "class", "method", "field"
- `old_name`: Original name with full path
  - class: "com.example.TestClass" or "wzp"
  - method: "com.example.TestClass.methodName" or "wzp.a"
  - field: "com.example.TestClass.fieldName" or "wzp.a"
- `new_name`: New name, supports two formats:
  - Symbol name only: "getName", "moduleName"
  - Full path: "wzp.getName", "wzp.moduleName" (system will automatically extract symbol name)

### Return Result

```json
{
    "success": true,
    "summary": {
        "total": 3,
        "successful": 3,
        "failed": 0
    },
    "failed_operations": [],
    "message": "Batch rename completed: 3 operations total, 3 successful, 0 failed"
}
```

### Usage Example

```python
# Batch rename example
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

## 📝 License

[![Stars](https://img.shields.io/github/stars/xi0yu/jebmcp?style=social)](https://github.com/xi0yu/jebmcp/stargazers)
[![Forks](https://img.shields.io/github/forks/xi0yu/jebmcp?style=social)](https://github.com/xi0yu/jebmcp/network/members)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=xi0yu/jebmcp&type=Date)](https://www.star-history.com/#xi0yu/jebmcp&Date)

---

## 🌍 More Resources

- [JEB Official Documentation](https://www.pnfsoftware.com/jeb/apidoc)  
- [MCP Documentation](https://mcp-docs.cn/introduction)  

Thank you for using JEBMCP, hope it helps you perform reverse engineering tasks more efficiently!