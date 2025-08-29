# JEB MCP 模块化架构说明

## 重构目标

将原来的单一 `MCP.py` 文件重构为模块化架构，实现职责分离，提高代码的可维护性和可读性。

## 新的目录结构

```
src/
├── MCP_refactored.py          # 重构后的主插件文件（推荐使用）
├── MCP.py                     # 原始文件（保留作为备份）
├── server.py                  # FastMCP 服务端（已简化）
├── core/                      # 核心业务逻辑层
│   ├── __init__.py
│   ├── project_manager.py     # 项目管理模块
│   └── jeb_operations.py      # JEB 业务操作模块
├── api/                       # API 接口层
│   ├── __init__.py
│   └── jsonrpc_handler.py     # JSON-RPC 请求处理
└── utils/                     # 工具函数层
    ├── __init__.py
    └── signature_utils.py     # JNI 签名工具
```

## 各模块职责

### 1. core/project_manager.py
- **职责**：管理 JEB 项目和单元
- **功能**：
  - 获取当前项目
  - 查找 APK/DEX 单元
  - 项目状态检查

### 2. core/jeb_operations.py
- **职责**：处理所有 JEB 相关的业务逻辑
- **功能**：
  - 获取 manifest
  - 反编译方法和类
  - 查找方法调用者和重写

### 3. api/jsonrpc_handler.py
- **职责**：处理 JSON-RPC 请求并委托给业务逻辑
- **功能**：
  - 路由请求到相应的业务方法
  - 参数验证
  - 错误处理

### 4. utils/signature_utils.py
- **职责**：JNI 签名转换和验证
- **功能**：
  - 验证 JNI 签名格式
  - 自动转换类名到 JNI 格式

### 5. MCP_refactored.py
- **职责**：插件管理和协调
- **功能**：
  - 初始化各个模块
  - 管理 HTTP 服务器
  - 协调模块间通信

## 重构优势

### 1. 职责清晰
- 每个模块只负责一个方面
- 业务逻辑与接口处理分离
- 项目管理与具体操作分离

### 2. 易于维护
- 修改某个功能不会影响其他部分
- 代码结构更清晰，易于理解
- 减少代码重复

### 3. 易于测试
- 可以单独测试业务逻辑
- 可以模拟依赖进行单元测试
- 更好的错误隔离

### 4. 易于扩展
- 新增功能只需在相应模块添加
- 可以轻松添加新的工具函数
- 支持插件化架构

## 使用方法

### 1. 使用重构版本
将 `MCP_refactored.py` 重命名为 `MCP.py`，或者在 JEB 中直接加载 `MCP_refactored.py`。

### 2. 添加新功能
- 在 `core/jeb_operations.py` 中添加新的业务方法
- 在 `api/jsonrpc_handler.py` 中添加新的路由
- 在 `server.py` 中添加新的 MCP 工具函数

### 3. 修改现有功能
- 业务逻辑修改：`core/jeb_operations.py`
- 接口修改：`api/jsonrpc_handler.py`
- 项目管理修改：`core/project_manager.py`

## 注意事项

1. **Python 2.7 兼容性**：所有模块都保持 Python 2.7 兼容
2. **导入路径**：使用绝对导入避免相对导入问题
3. **错误处理**：每层都有专门的错误处理机制
4. **向后兼容**：保持原有的 JSON-RPC 接口不变

## 迁移建议

1. 先测试重构版本是否正常工作
2. 确认所有功能都正常后，替换原始文件
3. 保留原始文件作为备份
4. 逐步熟悉新的模块结构
