import os
import sys
import ast
import json
import shutil
import argparse
import http.client

from fastmcp import FastMCP

# The log_level is necessary for Cline to work: https://github.com/jlowin/fastmcp/issues/81
mcp = FastMCP("github.com/flankerhqd/jeb-pro-mcp", log_level="ERROR")

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
        data = json.loads(response.read().decode())

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
def check_status():
    """Get detailed status information about JEB and loaded projects

    Returns comprehensive information including:
    - MCP to JEB connection status
    - Number of open projects
    - Project details (name, APK/DEX counts)
    - APK information (package name, version, file size, MD5)
    - DEX information (class count, method count)
    - JEB version information
    """
    return _jeb_call('check_status')

@mcp.tool()
def get_method_smali(class_signature, method_name):
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
def get_manifest():
    """Get the manifest of the currently loaded APK project in JEB"""
    return _jeb_call('get_manifest')

@mcp.tool()
def get_method_decompiled_code(method_signature):
    """Get the decompiled code of the given method in the currently loaded APK project
    Dex units use Java-style internal addresses to identify items:

    - package: Lcom/abc/
    - type: Lcom/abc/Foo;
    - method: Lcom/abc/Foo;->bar(I[JLjava/Lang/String;)V
    - field: Lcom/abc/Foo;->flag1:Z

    @param method_signature: the fully-qualified method signature to decompile, e.g. Lcom/abc/Foo;->bar(I[JLjava/Lang/String;)V
    """
    return _jeb_call('get_method_decompiled_code', method_signature)

@mcp.tool()
def get_class_decompiled_code(class_signature):
    """Get the decompiled code of a class in the current APK project.

    Input formats supported (auto-normalized to JNI signature):
    - Plain class name: e.g. "abjz"
    - Package + class with dots: e.g. "com.example.Foo"
    - JNI-style signature: e.g. "Lcom/example/Foo;"

    @param class_signature: Class identifier in any of the supported forms.
    """
    return _jeb_call('get_class_decompiled_code', class_signature)

@mcp.tool()
def get_method_callers(method_signature):
    """
    Get the callers of the given method in the currently loaded APK project
    """
    return _jeb_call('get_method_callers', method_signature)

@mcp.tool()
def get_method_overrides(method_signature):
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
def set_class_name(class_name, new_name=None):
    """Set the name of a class in the current APK project.

    If new_name is provided, it will rename the class. If not provided, it will return current class info.

    @param class_name: Class signature. Supports both:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param new_name: Optional new name for the class
    """
    return _jeb_call('set_class_name', class_name, new_name)

@mcp.tool()
def set_method_name(class_name, method_name, new_name=None):
    """Set the name of a method in the specified class.

    If new_name is provided, it will rename the method. If not provided, it will return current method info.

    @param class_name: Class signature. Supports both:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param method_name: Current name of the method
    @param new_name: Optional new name for the method
    """
    return _jeb_call('set_method_name', class_name, method_name, new_name)

@mcp.tool()
def set_field_name(class_signature, field_name, new_name=None):
    """Set the name of a field in the specified class.

    If new_name is provided, it will rename the field. If not provided, it will return current field info.

    @param class_name: Class signature. Supports both:
        - JNI format, e.g. Lcom/example/MyClass;
        - Java format, e.g. com.example.MyClass
    @param field_name: Current name of the field
    @param new_name: Optional new name for the field
    """
    return _jeb_call('set_field_name', class_signature, field_name, new_name)

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
                        help="MCP 传输协议：sse(默认)、http、stdio")
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
    main()