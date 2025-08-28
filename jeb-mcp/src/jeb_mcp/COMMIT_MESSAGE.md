# Git Commit Message

## 主要提交信息
```
feat: 重构JEB-MCP API设计，使用当前项目而非文件路径

- 移除所有函数的filepath参数，直接使用当前JEB项目
- 重构get_manifest、get_method_decompiled_code等核心函数
- 提升用户体验，符合JEB Pro工作流程
- 避免重复加载APK文件，提升性能
- 统一错误处理和状态检查逻辑
```

## 详细变更
```
重构JEB-MCP的API设计，使其更符合JEB Pro的工作流程：

### 主要变更
- get_manifest() - 移除filepath参数，直接获取当前项目manifest
- get_method_decompiled_code() - 移除filepath参数
- get_class_decompiled_code() - 移除filepath参数
- get_method_callers() - 移除filepath参数
- get_method_overrides() - 移除filepath参数

### 技术改进
- 使用engctx.getProject()获取当前项目
- 避免重复加载和解析APK文件
- 统一的错误处理和状态检查
- 更好的资源管理和性能

### 用户体验
- 无需提供文件路径
- 与JEB IDE使用习惯一致
- 更快的响应速度
- 减少参数错误

修改文件: MCP.py, server_generated.py
```

## 标签建议
- `feat:` - 新功能/重大改进
- `refactor:` - 代码重构
- `perf:` - 性能改进
- `breaking change:` - 破坏性变更
