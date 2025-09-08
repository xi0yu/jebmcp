# 🚀 JEBMCP: A Gateway to JEB and MCP Integration

Welcome to the **JEBMCP** repository! This project combines the power of JEB and MCP, facilitating reverse engineering tasks. It offers a suite of Python scripts to streamline your workflow, making it easier to analyze and manipulate code.

[![Stars](https://img.shields.io/github/stars/xi0yu/jebmcp?style=social)](https://github.com/xi0yu/jebmcp/stargazers)
[![Forks](https://img.shields.io/github/forks/xi0yu/jebmcp?style=social)](https://github.com/xi0yu/jebmcp/network/members)
## Star History
[![Star History Chart](https://api.star-history.com/svg?repos=xi0yu/jebmcp&type=Date)](https://www.star-history.com/#xi0yu/jebmcp&Date)
[![License](https://img.shields.io/github/license/xi0yu/jebmcp)](https://github.com/xi0yu/jebmcp/blob/master/LICENSE)


## 🌟 Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Features](#features)
5. [Contributing](#contributing)
6. [License](#license)
7. [Contact](#contact)
8. [Releases](#releases)

## 🧐 Introduction

**JEBMCP** 是一个将 JEB 反编译能力与 MCP（Minecraft Coder Pack）集成的工具，支持项目分析、方法/类重命名、获取方法调用关系等操作。  
本项目通过 JSON-RPC 或 SSE 与 JEB 交互，提供 Python 端工具调用接口。

## ⚙️ Installation

To get started with JEBMCP, follow these steps:

1. **Clone the Repository**
   ```bash
   git clone https://github.com/xi0yu/jebmcp.git
   ```
   
2. **Navigate to the Project Directory**
   ```bash
   cd jebmcp
   ```

3. **Install Required Dependencies**
   Make sure you have Python 3.x installed. Use pip to install the necessary packages.
   ```bash
   pip install -r requirements.txt
   ```

## 🛠️ 项目结构与用途说明

### server.py
- **用途**：专为支持 **Claude Code / Claude / Cursor** 等集成 MCP 的客户端工具准备。  
- **注意**：**不是命令行工具**，用户不需要手动运行 `python server.py`。  
- 它会在集成工具内部被调用，用于启动 MCP 服务和桥接 JEB 客户端接口。

### MCP.py
- **用途**：通过 **JEB 客户端** 运行脚本来调用 MCP 工具功能。  
- **注意**：**不支持直接命令行执行**。  
- 用户使用 JEB 内置的脚本运行功能，通过 `MCP.py` 来操作项目，例如获取方法调用关系、反编译类、重命名等。


## 🌈 Features

- **Integration**: Seamless connection between JEB and MCP.
- **Efficiency**: Optimized scripts for faster performance.
- **User-Friendly**: Easy-to-use command-line interface.
- **Customization**: Modify scripts to fit your specific needs.

## 🤝 Contributing

We welcome contributions! To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Push to the branch (`git push origin feature-branch`).
5. Open a pull request.

Please ensure that your code follows our guidelines for coding standards and testing.

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🌍 Explore More

For a deeper dive into JEB and MCP, check out the following resources:

- [JEB Official Documentation](https://www.pnfsoftware.com/jeb/apidoc)
- [MCP Documentation](https://mcp-docs.cn/introduction)

Thank you for checking out JEBMCP! We hope it helps you in your reverse engineering endeavors.
