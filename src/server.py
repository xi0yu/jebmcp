# -*- coding: utf-8 -*-
import os
import sys
import ast
import json
import shutil
import argparse
import http.client
import signal

from fastmcp import FastMCP

# The log_level is necessary for Cline to work: https://github.com/jlowin/fastmcp/issues/81
mcp = FastMCP("github.com/flankerhqd/jeb-pro-mcp")

jsonrpc_request_id = 1

def make_jsonrpc_request(method, *params, jeb_host="127.0.0.1", jeb_port=16161, jeb_path="/mcp"):
    """
    转发到本地 JEB 插件的 JSON-RPC 接口 (默认 http://127.0.0.1:16161/mcp)
    """
    global jsonrpc_request_id
    conn = http.client.HTTPConnection(jeb_host, jeb_port, timeout=30)
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": list(params),
        "id": jsonrpc_request_id,
    }
    jsonrpc_request_id += 1

    try:
        conn.request("POST", jeb_path, json.dumps(request), {
            "Content-Type": "application/json"
        })
        response = conn.getresponse()
        data = json.loads(response.read().decode("UTF-8"))

        if "error" in data:
            err = data["error"]
            code = err.get("code")
            message = err.get("message")
            pretty = f"JSON-RPC error {code}: {message}"
            if "data" in err:
                pretty += "\n" + err["data"]
            raise RuntimeError(pretty)

        result = data.get("result")
        # Claude/MCP 对空结果容忍度低，返回个“success”
        return "success" if result is None else result
    finally:
        conn.close()

# 通过一个统一的“调用包装器”把 CLI 参数里的 JEB 地址带进每个 tool
def _jeb_call(method, *params):
    return make_jsonrpc_request(
        method, *params,
        jeb_host=os.environ.get("JEB_HOST", "127.0.0.1"),
        jeb_port=int(os.environ.get("JEB_PORT", "16161")),
        jeb_path=os.environ.get("JEB_PATH", "/mcp"),
    )

# -----------------------------
#       MCP 工具定义
# -----------------------------

@mcp.tool()
def load_project(file_path: str):
    """Open a new APK/DEX project in JEB from the specified file path.
    
    This function will:
    1. Open the specified APK/DEX file as a new project in JEB
    2. Update the project manager context to work with the new project
    3. Return project information including file path, project name, and available units
    
    Args:
    - file_path (str): Absolute path to the APK/DEX file to open
        
    Returns:
    - dict: Contains success status, project information, and any error messages
    """
    try:
        result = _jeb_call('load_project', file_path)
        print(result)
        return result
    except Exception as e:
        print(f"Error loading project: {e}")
        return {"success": False, "error": str(e)}

@mcp.tool()
def has_projects():
    """Check if there are any projects loaded in JEB.

    Returns:
    - dict: Contains success status and a boolean indicating if projects exist
    """
    return _jeb_call('has_projects')

@mcp.tool()
def get_projects():
    """Get a list of all loaded projects in JEB.

    Returns:
    - dict: Contains success status and a list of project details
    """
    return _jeb_call('get_projects')

# @mcp.tool()
# def unload_projects():
#     """Unload all loaded projects in JEB.
# 
#     注意：此功能已被注释，因为 unload_projects 操作需要在 JEB 的 UI 线程中执行。
#     由于 SWT 线程模型的限制，项目卸载涉及 UI 组件的清理和状态更新，
#     否则会抛出 SWTException: Invalid thread access。
#     
#     如需卸载项目，请在 JEB 界面中手动操作，或者重启 JEB 应用程序。
# 
#     Returns:
#     - dict: Contains success status and a list of unloaded project details
#     """
#     return _jeb_call('unload_projects')


@mcp.tool()
def get_current_project_info():
    """Retrieve detailed information about the current JEB session and loaded projects.

    Returns a dictionary containing:
    - MCP to JEB connection status
    - Number of currently open projects
    - Project details (name, APK/DEX counts)
    - APK metadata (package name, version, file size, MD5)
    - DEX metadata (number of classes, methods)
    - JEB version information

    This function only retrieves information and does not modify any project.
    """
    return _jeb_call('get_current_project_info')

@mcp.tool()
def get_method_smali(class_signature: str, method_name: str):
    """Get all Smali instructions for a specific method in the given class

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    @param method_name: Name of the method to get Smali instructions for
    """
    return _jeb_call('get_method_smali', class_signature, method_name)

@mcp.tool()
def ping():
    """Do a simple ping to check server is alive and running"""
    try:
        _ = _jeb_call("ping")
        return "Successfully connected to JEB Pro"
    except Exception:
        shortcut = "Ctrl+Option+M" if sys.platform == "darwin" else "Ctrl+Alt+M"
        return f"Failed to connect to JEB Pro! Did you run Edit -> Scripts -> MCP ({shortcut}) to start the server?"

@mcp.tool()
def get_app_manifest():
    """Get the manifest of the currently loaded APK project in JEB"""
    return _jeb_call('get_app_manifest')

@mcp.tool()
def get_method_decompiled_code(class_name: str, method_name: str):
    """Get the decompiled code of the given method in the currently loaded APK project
    
    Supports multiple class name formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_name: Class identifier in any of the supported forms
    @param method_name: Name of the method to decompile (e.g. "onCreate", "onClick", "find")
    """
    return _jeb_call('get_method_decompiled_code', class_name, method_name)

@mcp.tool()
def get_class_decompiled_code(class_signature: str):
    """Get the decompiled code of a class in the current APK project.

    Input formats supported (auto-normalized to JNI signature):
    - Plain class name: e.g. "abjz"
    - Package + class with dots: e.g. "com.example.Foo"
    - JNI-style signature: e.g. "Lcom/example/Foo;"

    @param class_signature: Class identifier in any of the supported forms.
    """
    return _jeb_call('get_class_decompiled_code', class_signature)

@mcp.tool()
def get_method_callers(class_name: str, method_name: str):
    """Get the callers/references of the given method in the currently loaded APK project
    @param class_name: class name in either Dalvik JNI signature (e.g. Lcom/example/Foo;) 
                       or normal Java style (e.g. com.example.Foo)
    @param method_name: the method name (e.g. bar)
    """
    return _jeb_call('get_method_callers', class_name, method_name)

@mcp.tool()
def get_method_overrides(method_signature: str):
    """Get the overrides of the given method in the currently loaded APK project

    @param method_signature: the fully-qualified method signature to find overrides for, e.g. Lcom/example/Foo;->bar(I[JLjava/Lang/String;)V
    """
    return _jeb_call('get_method_overrides', method_signature)

@mcp.tool()
def get_field_callers(class_name: str, field_name: str):
    """Get the callers/references of the given field in the currently loaded APK project.

    @param class_name: class name in either Dalvik JNI signature (e.g. Lcom/example/Foo;) 
                       or normal Java style (e.g. com.example.Foo)
    @param field_name: the field name (e.g. flag1)
    """
    return _jeb_call('get_field_callers', class_name, field_name)

@mcp.tool()
def rename_class_name(class_name: str, new_name: str):
    """Rename a class in the current APK project.

    This function requires a new_name to perform renaming. 
    If new_name is not provided, an error will be raised.

    @param class_name: Class signature. Supports both formats:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param new_name: Optional new class name
    """
    return _jeb_call('rename_class_name', class_name, new_name)

@mcp.tool()
def rename_method_name(class_name: str, method_name: str, new_name: str):
    """Rename a method in the specified class of the current APK project.

    This function requires a new_name to perform renaming. 
    If new_name is not provided, an error will be raised.

    @param class_name: Class signature. Supports both formats:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param method_name: Original name of the method to rename
    @param new_name: New method name to set (required)
    """
    return _jeb_call('rename_method_name', class_name, method_name, new_name)

@mcp.tool()
def rename_field_name(class_name: str, field_name: str, new_name: str):
    """Rename a field in the specified class of the current APK project.

    This function requires a new_name to perform renaming. 
    If new_name is not provided, an error will be raised.

    @param class_name: Class signature. Supports both formats:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param field_name: Original name of the field to rename
    @param new_name: New field name to set (required)
    """
    return _jeb_call('rename_field_name', class_name, field_name, new_name)

@mcp.tool()
def get_class_type_tree(class_signature: str, max_node_count: int=16):
    """Build a hierarchical type tree for a class showing inheritance relationships.

    This function analyzes a class and builds a tree structure showing:
    - Superclass hierarchy
    - Implemented interfaces
    - Inner classes
    - Fields and methods (limited for performance)

    @param class_signature: Class identifier. Supports multiple formats:
        - Plain class name: e.g. "MainActivity"
        - Package + class with dots: e.g. "com.example.MainActivity"
        - JNI-style signature: e.g. "Lcom/example/MainActivity;"
    @param max_node_count: Maximum number of nodes to traverse (default: 16)
    """
    return _jeb_call('get_class_type_tree', class_signature, max_node_count)

@mcp.tool()
def get_class_superclass(class_signature: str):
    """Get the superclass of a given class.

    This function analyzes a class and returns information about its direct superclass.
    Useful for understanding inheritance hierarchy and class relationships.

    @param class_signature: Class identifier. Supports multiple formats:
        - Plain class name: e.g. "MainActivity"
        - Package + class with dots: e.g. "com.example.MainActivity"
        - JNI-style signature: e.g. "Lcom/example/MainActivity;"
    """
    return _jeb_call('get_class_superclass', class_signature)

@mcp.tool()
def get_class_interfaces(class_signature: str):
    """Get all interfaces implemented by a given class.

    This function analyzes a class and returns a list of all interfaces it implements,
    including both directly implemented and inherited interfaces.

    @param class_signature: Class identifier. Supports multiple formats:
        - Plain class name: e.g. "MainActivity"
        - Package + class with dots: e.g. "com.example.MainActivity"
        - JNI-style signature: e.g. "Lcom/example/MainActivity;"
    """
    return _jeb_call('get_class_interfaces', class_signature)

@mcp.tool()
def parse_protobuf_class(class_signature: str):
    """Parse protobuf definition for a specific class.

    Supports multiple class signature formats:
    - Plain class name: e.g. "ProtoMessage"
    - Package + class with dots: e.g. "com.example.ProtoMessage"
    - JNI-style signature: e.g. "Lcom/example/ProtoMessage;"

    @param class_signature: Class identifier in any of the supported forms
    """
    return make_jsonrpc_request('parse_protobuf_class', class_signature)

@mcp.tool()
def get_class_methods(class_signature: str):
    """Get all methods of a given class.

    This function analyzes a class and returns detailed information about all its methods,
    including method signatures, return types, parameters, and access modifiers.

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    """
    return _jeb_call('get_class_methods', class_signature)

@mcp.tool()
def get_class_fields(class_signature: str):
    """Get all fields of a given class.

    This function analyzes a class and returns detailed information about all its fields,
    including field types, access modifiers, and initial values when available.

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    """
    return _jeb_call('get_class_fields', class_signature)

@mcp.tool(name="rename_batch_symbols", description="批量重命名类/字段/方法")
def rename_batch_symbols(rename_operations: str):
    """
    批量重命名类、方法和字段（JSON 输入格式说明）

    参数：
        rename_operations (str): ⚠️ 必须是 JSON 数组格式字符串，每个元素代表一次重命名操作。
    
    JSON 元素字段：
        - type (str): 重命名类型，可选值：
            "class"  → 表示重命名类
            "method" → 表示重命名方法
            "field"  → 表示重命名字段
        - old_name (str): 旧名称，完整路径
            - class: "com.example.TestClass" 或 "wzp"
            - method: "com.example.TestClass.methodName" 或 "wzp.a"
            - field: "com.example.TestClass.fieldName" 或 "wzp.a"
        - new_name (str): 新名称，支持两种格式
            - 符号名: "getName", "moduleName"
            - 完整路径: "wzp.getName" (系统会自动提取符号名称)
    
    示例输入：
    [
        {"type": "class", "old_name": "com.example.TestClass", "new_name": "RenamedTestClass"},
        {"type": "method", "old_name": "com.example.TestClass.testMethod", "new_name": "renamedTestMethod"},
        {"type": "field", "old_name": "com.example.TestClass.testField", "new_name": "renamedTestField"}
    ]

    注意事项：
    1. JSON 必须是数组，不能是单个对象。
    2. 所有操作必须在同一个数组里提供。
    3. new_name 可以是符号名或完整路径，系统会自动提取符号名。
    4. 如果格式错误或字段缺失，操作会停止并返回失败信息。

    返回：
        dict: 包含操作结果，包括成功标志、操作统计、失败操作列表和消息。
    """
    return _jeb_call('rename_batch_symbols', rename_operations)


# 可选：为 HTTP/健康检查提供一个简单路由（仅在 transport=http 时可见）
@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    from starlette.responses import PlainTextResponse
    return PlainTextResponse("OK")

# -----------------------------
#          入口与参数
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="JEB Pro MCP Server (SSE/HTTP)")
    parser.add_argument("--transport", choices=["sse", "http", "stdio"], default=os.environ.get("TRANSPORT", "stdio"),
                        help="MCP 传输协议：sse、http、stdio(默认)")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"),
                        help="对外绑定地址（sse/http 有效）")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "16162")),
                        help="对外端口（sse/http 有效，默认 16162，避免与 JEB 的 16161 冲突）")
    # JEB 侧转发地址（如你改动了 JEB 的端口或路径，可覆写）
    parser.add_argument("--jeb-host", default=os.environ.get("JEB_HOST", "127.0.0.1"))
    parser.add_argument("--jeb-port", type=int, default=int(os.environ.get("JEB_PORT", "16161")))
    parser.add_argument("--jeb-path", default=os.environ.get("JEB_PATH", "/mcp"))
    args = parser.parse_args()

    # 把 JEB 目标写回到环境变量，供 _jeb_call 使用（避免在每个 tool 签名里加参数）
    os.environ["JEB_HOST"] = args.jeb_host
    os.environ["JEB_PORT"] = str(args.jeb_port)
    os.environ["JEB_PATH"] = args.jeb_path

    if args.transport == "stdio":
        # 兼容原来的 stdio 模式（Claude CLI: claude mcp add NAME -- python server.py）
        mcp.run(transport="stdio")
    elif args.transport == "http":
        # Streamable HTTP（推荐），端点为 http://host:port/mcp/
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        # SSE（legacy，但 Claude CLI 完整支持），端点为 http://host:port/sse
        mcp.run(transport="sse", host=args.host, port=args.port)

if __name__ == "__main__":
    # 注意：Ctrl+C 关闭 SSE 服务器时可能会显示一些 CancelledError 堆栈
    # 这是 FastMCP/uvicorn 的已知行为，不影响服务器正常关闭
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        # 优雅退出，不显示额外错误
        pass