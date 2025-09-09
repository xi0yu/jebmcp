# -*- coding: utf-8 -*-
"""
Protobuf解析功能使用示例
展示如何通过MCP调用protobuf解析功能
"""

import json
import requests

def test_protobuf_parsing():
    """测试protobuf解析功能"""
    
    # MCP服务器地址
    mcp_url = "http://localhost:16161/mcp"
    
    # 测试数据
    test_cases = [
        {
            "name": "测试基本protobuf类解析",
            "method": "parse_protobuf_class",
            "params": ["com.example.ProtoMessage"]
        },
        {
            "name": "测试JNI格式类签名",
            "method": "parse_protobuf_class", 
            "params": ["Lcom/example/ProtoMessage;"]
        },
        {
            "name": "测试不存在的类",
            "method": "parse_protobuf_class",
            "params": ["Lcom/nonexistent/Class;"]
        }
    ]
    
    print("=== Protobuf解析功能测试 ===\n")
    
    for test_case in test_cases:
        print(f"测试: {test_case['name']}")
        print(f"方法: {test_case['method']}")
        print(f"参数: {test_case['params']}")
        
        # 构建JSON-RPC请求
        request = {
            "jsonrpc": "2.0",
            "method": test_case['method'],
            "params": test_case['params'],
            "id": 1
        }
        
        try:
            # 发送请求
            response = requests.post(
                mcp_url,
                json=request,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"响应状态: {response.status_code}")
                print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"错误: HTTP {response.status_code}")
                print(f"响应: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
        except Exception as e:
            print(f"处理失败: {e}")
        
        print("-" * 50)

def show_usage_examples():
    """显示使用示例"""
    print("=== Protobuf解析功能使用说明 ===\n")
    
    print("1. 通过JSON-RPC调用:")
    print("""
    POST http://localhost:16161/mcp
    Content-Type: application/json
    
    {
        "jsonrpc": "2.0",
        "method": "parse_protobuf_class",
        "params": ["com.example.ProtoMessage"],
        "id": 1
    }
    """)
    
    print("2. 支持的类签名格式:")
    print("   - Java格式: com.example.ProtoMessage")
    print("   - JNI格式: Lcom/example/ProtoMessage;")
    print("   - 自动转换: 系统会自动处理格式转换")
    
    print("3. 返回结果格式:")
    print("""
    {
        "jsonrpc": "2.0",
        "result": {
            "success": true,
            "class_signature": "Lcom/example/ProtoMessage;",
            "proto_definition": "message ProtoMessage {\\n\\toptional int32 field1 = 1;\\n\\toptional string field2 = 2;\\n}\\n",
            "message": "Protobuf definition parsed successfully"
        },
        "id": 1
    }
    """)
    
    print("4. 错误处理:")
    print("""
    {
        "jsonrpc": "2.0",
        "result": {
            "success": false,
            "error": "Class not found: Lcom/nonexistent/Class;"
        },
        "id": 1
    }
    """)

if __name__ == "__main__":
    show_usage_examples()
    print("\n")
    test_protobuf_parsing()
