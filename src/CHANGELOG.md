# JEB-MCP Changelog

## [2025-08-29] 架构重构和 Python 2.7 兼容性优化

### 🚀 主要改进
- **架构重构**: 将 `MCP.py` 从单体架构重构为模块化架构
- **职责分离**: 创建 `core/`, `api/`, `utils/` 三个核心模块
- **配置驱动**: 实现基于 `method_registry.py` 的方法注册表系统
- **Python 2.7 兼容**: 修复所有 Python 3 语法，确保在 JEB 环境中正常运行

### 🏗️ 新架构组件
- **`core/project_manager.py`**: JEB 项目和单元管理
- **`core/jeb_operations.py`**: 核心业务逻辑操作
- **`api/jsonrpc_handler.py`**: JSON-RPC 请求处理
- **`api/method_registry.py`**: 方法定义配置
- **`utils/signature_utils.py`**: JNI 签名工具函数

### 🔧 技术优化
- **消除多重 if-else**: 使用配置驱动和动态调用替代条件判断
- **统一参数验证**: 实现装饰器模式的参数验证机制
- **类型安全**: 支持参数类型和返回类型定义
- **文档友好**: 自动生成方法签名和描述信息

### 🐛 问题修复
- **导入兼容性**: 修复相对导入问题，添加 fallback 机制
- **语法兼容性**: 移除 f-string、类型注解等 Python 3 特性
- **类继承**: 所有类继承自 `object` 确保 Python 2.7 兼容
- **错误处理**: 增强参数验证和异常处理

### 📁 文件变更
- **新增**: `src/core/`, `src/api/`, `src/utils/` 目录结构
- **重构**: `src/MCP.py` 主文件架构
- **合并**: 将 `server_generated.py` 内容合并到 `server.py`
- **删除**: 移除冗余的 `server_generated.py` 文件

### 🎯 架构优势
- **可维护性**: 清晰的模块分离和职责划分
- **可扩展性**: 添加新方法只需修改配置文件
- **可测试性**: 每层都可以独立测试
- **代码质量**: 消除重复代码，提高可读性

## [2025-08-28] 支持 JNI 签名归一化与项目/单元获取方式更新

### 变更
- 在 `get_class_decompiled_code` 中新增 JNI 签名辅助方法与自动归一化。
- 该函数现在支持三种输入：普通类名（如 "abjz"）、包点分格式（如 "com.example.Foo"）以及 JNI 签名（如 "Lcom/example/Foo;"）。
- 统一改为使用 `CTX.getMainProject()` 获取当前项目。
- 在各 RPC 方法中通过 `project.findUnit(IApkUnit)` 与 `project.findUnit(IDexUnit)` 获取 APK/Dex 单元：
  - `get_manifest`
  - `get_method_decompiled_code`
  - `get_class_decompiled_code`
  - `get_method_callers`
  - `get_method_overrides`
- 更新相关文档与服务端桩代码，反映新的输入兼容性。

### 原因
- 与 JEB 的运行时模型保持一致，避免依赖已废弃或不正确的引擎调用。
- 通过支持多种类标识输入，提升开发者体验。
- 提升代码/单元查找的稳定性与可靠性。


## [2024-12-19] 重大架构改进 - 使用当前JEB项目而非文件路径

### 🎯 改进目标
重构JEB-MCP的API设计，使其更符合JEB Pro的工作流程，提升用户体验和性能。

### 🔄 主要变更

#### 1. 函数签名简化
- **`get_manifest()`** - 移除 `filepath` 参数，直接获取当前项目manifest
- **`get_method_decompiled_code(method_signature)`** - 移除 `filepath` 参数
- **`get_class_decompiled_code(class_signature)`** - 移除 `filepath` 参数  
- **`get_method_callers(method_signature)`** - 移除 `filepath` 参数
- **`get_method_overrides(method_signature)`** - 移除 `filepath` 参数

#### 2. 架构优化
- **使用当前项目**: 通过 `engctx.getProject()` 获取当前JEB项目
- **避免重复加载**: 不再创建新的项目实例
- **资源复用**: 利用已经加载的APK单元
- **更好的错误处理**: 提供更清晰的错误信息

#### 3. 用户体验提升
- **无需文件路径**: 用户不需要记住或提供APK文件路径
- **符合JEB工作流**: 与JEB IDE的使用习惯完全一致
- **更快的响应**: 避免重复加载APK文件

### 📝 修改的文件

#### `MCP.py`
- 重构 `get_manifest()` 函数
- 重构 `get_method_decompiled_code()` 函数
- 重构 `get_class_decompiled_code()` 函数
- 重构 `get_method_callers()` 函数
- 重构 `get_method_overrides()` 函数
- 统一使用当前项目获取APK单元的逻辑

#### `server_generated.py`
- 更新所有MCP工具的函数签名
- 移除 `filepath` 参数
- 更新函数文档说明

### 💡 设计优势

1. **更符合JEB生态**: 与JEB Pro的工作流程完全一致
2. **性能提升**: 避免重复加载和解析APK文件
3. **用户体验**: 简化API调用，减少参数错误
4. **资源管理**: 更好的内存和资源使用
5. **错误处理**: 更清晰的错误信息和状态检查

### 🚀 新的使用方式

```python
# 获取当前项目的manifest
manifest = get_manifest()

# 获取特定方法的反编译代码
code = get_method_decompiled_code("Lcom/example/MainActivity;->onCreate(Landroid/os/Bundle;)V")

# 获取特定类的反编译代码
class_code = get_class_decompiled_code("Lcom/example/MainActivity;")

# 获取方法的调用者
callers = get_method_callers("Lcom/example/MainActivity;->onCreate(Landroid/os/Bundle;)V")

# 获取方法的重写
overrides = get_method_overrides("Lcom/example/MainActivity;->onCreate(Landroid/os/Bundle;)V")
```

### 🔧 技术细节

- 使用 `CTX.getEnginesContext().getProject()` 获取当前项目
- 遍历 `project.getLiveArtifacts()` 查找APK单元
- 统一的错误处理和状态检查
- 保持向后兼容的JSON-RPC接口

### 📋 待办事项

- [ ] 测试所有重构后的函数
- [ ] 验证错误处理逻辑
- [ ] 更新项目文档
- [ ] 考虑添加项目状态检查工具

---

*此更新日志记录了JEB-MCP项目的重要架构改进，旨在提升用户体验和系统性能。*
