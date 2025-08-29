# -*- coding: utf-8 -*-
"""
Usage example for the new JSON-RPC handler architecture
"""
from jsonrpc_handler import JSONRPCHandler
from method_registry import get_method_info, get_all_methods

def demonstrate_new_architecture():
    """Demonstrate the new architecture capabilities"""
    
    # 模拟 JEB 操作对象
    class MockJebOperations(object):
        def get_manifest(self):
            return "<?xml version='1.0' encoding='utf-8'?>..."
        
        def get_class_decompiled_code(self, class_signature):
            return "public class {0} {{ ... }}".format(class_signature)
    
    # 创建处理器
    jeb_ops = MockJebOperations()
    handler = JSONRPCHandler(jeb_ops)
    
    print("=== 新架构演示 ===\n")
    
    # 1. 获取所有支持的方法
    print("1. 支持的方法列表:")
    methods = handler.get_supported_methods()
    for method in methods:
        print("   - {0}: {1}".format(method['method'], method['description']))
        print("     参数: {0} (类型: {1})".format(method['param_names'], method['param_types']))
        print("     返回: {0}".format(method['return_type']))
        print()
    
    # 2. 获取特定方法信息
    print("2. 方法详细信息:")
    method_info = handler.get_method_info("get_class_decompiled_code")
    if method_info:
        print("   方法: {0}".format(method_info['method']))
        print("   描述: {0}".format(method_info['description']))
        print("   参数: {0}".format(method_info['param_names']))
        print("   类型: {0}".format(method_info['param_types']))
        print("   返回: {0}".format(method_info['return_type']))
        print()
    
    # 3. 获取方法签名
    print("3. 方法签名:")
    signature = handler.get_method_signature("get_class_decompiled_code")
    print("   {0}".format(signature))
    print()
    
    # 4. 测试方法调用
    print("4. 测试方法调用:")
    try:
        # 正常调用
        result = handler.handle_request("get_class_decompiled_code", ["abjz"])
        print("   正常调用结果: {0}...".format(result[:50]))
        
        # 参数不足的错误
        try:
            handler.handle_request("get_class_decompiled_code", [])
        except ValueError as e:
            print("   参数不足错误: {0}".format(e))
        
        # 未知方法错误
        try:
            handler.handle_request("unknown_method", [])
        except ValueError as e:
            print("   未知方法错误: {0}".format(e))
            
    except Exception as e:
        print("   调用错误: {0}".format(e))
    
    print("\n=== 架构优势 ===")
    print("✅ 配置驱动：方法定义集中在 method_registry.py")
    print("✅ 无 if-else：使用动态调用和配置映射")
    print("✅ 参数验证：统一的参数验证机制")
    print("✅ 易于扩展：添加新方法只需修改配置文件")
    print("✅ 类型安全：支持参数类型和返回类型定义")
    print("✅ 文档友好：自动生成方法签名和描述")

if __name__ == "__main__":
    demonstrate_new_architecture()
