# JEB-MCP Changelog

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
