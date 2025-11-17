# -*- coding: utf-8 -*-
import os
import sys
import ast
import json
import uuid
import shutil
import argparse
import http.client

from fastmcp import FastMCP

mcp = FastMCP()

def make_jsonrpc_request(method, *params, jeb_host="127.0.0.1", jeb_port=16161, jeb_path="/mcp"):
    """
    转发到本地 JEB 插件的 JSON-RPC 接口 (默认 http://127.0.0.1:16161/mcp)
    """
    conn = http.client.HTTPConnection(jeb_host, jeb_port, timeout=30)
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": list(params),
        "id": str(uuid.uuid4()),
    }

    try:
        conn.request("POST", jeb_path, json.dumps(request), {
            "Content-Type": "application/json"
        })
        response = conn.getresponse()
        data = json.loads(response.read().decode("UTF-8"))

        if "error" in data:
            err = data["error"]
            
            if isinstance(err, dict):
                code = err.get("code")
                message = err.get("message")
                pretty = "JSON-RPC error {}: {}".format(code, message)
                if "data" in err:
                    pretty += "\n" + err["data"]
            else:
                pretty = str(err)
            raise RuntimeError(
                "Exception during JSON-RPC request '{}': {}\nHint: Please update MCP plugin from GitHub to avoid API mismatches.".format(
                    method, pretty
                )
            )

        result = data.get("result")
        return "success" if result is None else result
    
    except Exception as e:
        raise RuntimeError(
            "Exception during JSON-RPC request '{}': {}\nHint: Please update MCP plugin from GitHub to avoid API mismatches.".format(method, e)
        )
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
def load_jeb_project(apk_or_dex_path: str):
    """
    Open an APK or DEX file as a new project in JEB.

    This function loads the specified APK/DEX in JEB, updates the project manager
    context to work with the new project, and returns project information.
    """
    try:
        result = _jeb_call('load_project', apk_or_dex_path)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def has_projects():
    """
    Check if there are any projects currently loaded in JEB.
    """
    return _jeb_call('has_projects')


@mcp.tool()
def get_projects():
    """
    Retrieve a list of all projects currently loaded in JEB.
    """
    return _jeb_call('get_projects')


@mcp.tool()
def get_current_project_info():
    """
    Retrieve detailed information about the current JEB session and loaded projects.

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
def get_method_smali_code(class_signature: str, method_name: str):
    """
    Get all Smali instructions for a specific method in the given class

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
    """
    Do a simple ping to check server is alive and running"""
    try:
        _ = _jeb_call("ping")
        return "Successfully connected to JEB Pro"
    except Exception:
        shortcut = "Ctrl+Option+M" if sys.platform == "darwin" else "Ctrl+Alt+M"
        return f"Failed to connect to JEB Pro! Did you run Edit -> Scripts -> MCP ({shortcut}) to start the server?"

@mcp.tool()
def get_current_app_manifest():
    """
    Get the manifest of the currently loaded APK project in JEB"""
    return _jeb_call('get_app_manifest')

@mcp.tool()
def get_method_decompiled_code(class_name: str, method_name: str):
    """
    Get the decompiled code of the given method in the currently loaded APK project
    
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
    """
    Get the decompiled code of a class in the current APK project.

    Input formats supported (auto-normalized to JNI signature):
    - Plain class name: e.g. "abjz"
    - Package + class with dots: e.g. "com.example.Foo"
    - JNI-style signature: e.g. "Lcom/example/Foo;"

    @param class_signature: Class identifier in any of the supported forms.
    """
    return _jeb_call('get_class_decompiled_code', class_signature)

@mcp.tool()
def get_method_callers(class_name: str, method_name: str):
    """
    Get all callers of the specified method in the currently loaded APK project.
    @param class_name: class name in either Dalvik JNI signature (e.g. Lcom/example/Foo;) 
                       or normal Java style (e.g. com.example.Foo)
    @param method_name: the method name (e.g. bar)
    """
    return _jeb_call('get_method_callers', class_name, method_name)

@mcp.tool()
def get_method_overrides(method_signature: str):
    """
    Get the overrides of the given method in the currently loaded APK project

    @param method_signature: the fully-qualified method signature to find overrides for, e.g. Lcom/example/Foo;->bar(I[JLjava/Lang/String;)V
    """
    return _jeb_call('get_method_overrides', method_signature)

@mcp.tool()
def get_field_callers(class_name: str, field_name: str):
    """
    Get the callers/references of the given field in the currently loaded APK project.

    @param class_name: class name in either Dalvik JNI signature (e.g. Lcom/example/Foo;) 
                       or normal Java style (e.g. com.example.Foo)
    @param field_name: the field name (e.g. flag1)
    """
    return _jeb_call('get_field_callers', class_name, field_name)

@mcp.tool()
def rename_class_name(class_name: str, new_name: str, keep_prefix: bool=True):
    """
    Rename a class in the current APK project.

    This function requires a new_name to perform renaming. 
    If new_name is not provided, an error will be raised.

    @param class_name: Class signature. Supports both formats:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param new_name: Optional new class name
    @param keep_prefix: Optional flag to keep the original class name prefix
    """
    return _jeb_call('rename_class_name', class_name, new_name, keep_prefix)

@mcp.tool()
def rename_method_name(class_name: str, method_name: str, new_name: str, keep_prefix: bool=True):
    """
    Rename a method in the specified class of the current APK project.

    This function requires a new_name to perform renaming. 
    If new_name is not provided, an error will be raised.

    @param class_name: Class signature. Supports both formats:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param method_name: Original name of the method to rename
    @param new_name: New method name to set (required)
    @param keep_prefix: Optional flag to keep the original method name prefix
    """
    return _jeb_call('rename_method_name', class_name, method_name, new_name, keep_prefix)

@mcp.tool()
def rename_field_name(class_name: str, field_name: str, new_name: str, keep_prefix: bool=True):
    """
    Rename a field in the specified class of the current APK project.

    This function requires a new_name to perform renaming. 
    If new_name is not provided, an error will be raised.

    @param class_name: Class signature. Supports both formats:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param field_name: Original name of the field to rename
    @param new_name: New field name to set (required)
    @param keep_prefix: Optional flag to keep the original field name prefix
    """
    return _jeb_call('rename_field_name', class_name, field_name, new_name, keep_prefix)

@mcp.tool()
def get_class_type_tree(class_signature: str, max_node_count: int=16):
    """
    Build a hierarchical type tree for a class showing inheritance relationships.

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
    """
    Get the direct superclass of a specified class in the currently loaded APK project.

    @param class_signature: Class identifier. Supports multiple formats:
        - Plain class name: e.g. "MainActivity"
        - Package + class with dots: e.g. "com.example.MainActivity"
        - JNI-style signature: e.g. "Lcom/example/MainActivity;"
    """
    return _jeb_call('get_class_superclass', class_signature)

@mcp.tool()
def get_class_interfaces(class_signature: str):
    """
    Get all interfaces implemented by a specified class in the currently loaded APK project.

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
    """
    Get all methods of a specified class in the currently loaded APK project.

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    """
    return _jeb_call('get_class_methods', class_signature)

@mcp.tool()
def get_class_fields(class_signature: str):
    """
    Get all fields of a specified class in the currently loaded APK project.

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    """
    return _jeb_call('get_class_fields', class_signature)

@mcp.tool()
def is_class_renamed(class_signature: str):
    """
    Check if the specified class has been renamed in the currently loaded APK project.

    @param class_signature: Class identifier in any supported format
    """
    return _jeb_call('is_class_renamed', class_signature)


@mcp.tool()
def is_method_renamed(class_signature: str, method_name: str):
    """
    Check if the specified method in the given class has been renamed.

    @param class_signature: Class identifier in any supported format
    @param method_name: Method name to check
    """
    return _jeb_call('is_method_renamed', class_signature, method_name)


@mcp.tool()
def is_field_renamed(class_signature: str, field_name: str):
    """
    Check if the specified field in the given class has been renamed.

    @param class_signature: Class identifier in any supported format
    @param field_name: Field name to check
    """
    return _jeb_call('is_field_renamed', class_signature, field_name)

@mcp.tool()
def set_parameter_name(class_signature: str, method_name: str, index: int, name: str, fail_on_conflict: bool = True, notify: bool = True):
    """
    Set a custom name for a parameter in the specified method of a class.

    @param class_signature: Class identifier (supports plain name, Java style, or JNI signature)
    @param method_name: Name of the method
    @param index: 0-based parameter index (excluding 'this')
    @param name: The new parameter name to set
    @param fail_on_conflict: If True, will fail if the name conflicts with existing variables
    @param notify: If True, listeners are notified if the name changes
    @return: Boolean indicating whether the name was effectively changed
    """
    return make_jsonrpc_request('set_parameter_name', class_signature, method_name, index, name, fail_on_conflict, notify)

@mcp.tool()
def reset_parameter_name(class_signature: str, method_name: str, index: int, notify: bool = True):
    """
    Reset a parameter name to its default value in the specified method of a class.

    @param class_signature: Class identifier (supports plain name, Java style, or JNI signature)
    @param method_name: Name of the method
    @param index: 0-based parameter index (excluding 'this')
    @param notify: If True, listeners are notified if the name changes
    @return: Boolean indicating whether the name was effectively reset
    """
    return make_jsonrpc_request('set_parameter_name', class_signature, method_name, index, None, False, notify)


@mcp.tool()
def find_class(class_signature: str):
    """
    Find a class in the currently loaded APK project.

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    """
    return _jeb_call('find_class', class_signature)

@mcp.tool()
def find_method(class_signature: str, method_name: str):
    """
    Find a method in the currently loaded APK project.

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    @param method_name: Name of the method to find
    """
    return _jeb_call('find_method', class_signature, method_name)

@mcp.tool()
def find_field(class_signature: str, field_name: str):
    """
    Find a field in the currently loaded APK project.

    Supports multiple class signature formats:
    - Plain class name: e.g. "MainActivity"
    - Package + class with dots: e.g. "com.example.MainActivity"
    - JNI-style signature: e.g. "Lcom/example/MainActivity;"

    @param class_signature: Class identifier in any of the supported forms
    @param field_name: Name of the field to find
    """
    return _jeb_call('find_field', class_signature, field_name)




def main():
    parser = argparse.ArgumentParser(description="JEB Pro MCP Server (SSE/HTTP)")
    parser.add_argument("--transport", choices=["sse", "http", "stdio"], default=os.environ.get("TRANSPORT", "stdio"),
                        help="MCP transport type: [sse、http、stdio] (default: stdio)")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"),
                        help="host server bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "16162")),
                        help="host server bind port (default: 16162)")
                        
    parser.add_argument("--jeb-host", default=os.environ.get("JEB_HOST", "127.0.0.1"))
    parser.add_argument("--jeb-port", type=int, default=int(os.environ.get("JEB_PORT", "16161")))
    parser.add_argument("--jeb-path", default=os.environ.get("JEB_PATH", "/mcp"))
    args = parser.parse_args()

    os.environ["JEB_HOST"] = args.jeb_host
    os.environ["JEB_PORT"] = str(args.jeb_port)
    os.environ["JEB_PATH"] = args.jeb_path

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport="sse", host=args.host, port=args.port)

if __name__ == "__main__":
    main()