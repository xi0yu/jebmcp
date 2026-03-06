# -*- coding: utf-8 -*-
"""
JEBMCP Server - MCP server with GZIP compression support for JSON-RPC
"""
import os
import sys
import gzip
import json
import uuid
import argparse
import http.client
import threading
import socket

from fastmcp import FastMCP

mcp = FastMCP()


class ConnectionPool:
    """HTTP 连接池，用于复用连接，提高性能"""
    def __init__(self):
        self._connections = {}
        self._lock = threading.Lock()

    def get_connection(self, host: str, port: int, timeout: int = 30):
        """获取连接，如果不存在则创建"""
        key = f"{host}:{port}"
        with self._lock:
            if key not in self._connections:
                self._connections[key] = http.client.HTTPConnection(host, port, timeout=timeout)
            return self._connections[key]


_connection_pool = ConnectionPool()


# GZIP 压缩阈值（字节）
COMPRESSION_THRESHOLD = 256


def make_jsonrpc_request(
    method: str,
    *params,
    jeb_host: str = "127.0.0.1",
    jeb_port: int = 16161,
    jeb_path: str = "/mcp",
    timeout: int = 30,
    use_compression: bool = True
) -> str:
    """
    转发到本地 JEB 插件的 JSON-RPC 接口 (默认 http://127.0.0.1:16161/mcp)
    统一处理所有异常，确保返回字符串结果

    Args:
        use_compression: 是否对大请求/响应使用 gzip 压缩
    """
    try:
        # 验证方法名
        if not isinstance(method, str) or not method.strip():
            return json.dumps({"error": "Invalid method name"})

        # 验证参数是否可序列化
        json_params = list(params)
        try:
            json.dumps(json_params)
        except (TypeError, ValueError) as e:
            return json.dumps({"error": f"Parameter validation failed: {str(e)}"})

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": json_params,
            "id": str(uuid.uuid4()),
        }

        request_body = json.dumps(request)
        request_bytes = request_body.encode("utf-8")

        # 从连接池获取连接
        conn = _connection_pool.get_connection(jeb_host, jeb_port, timeout=timeout)

        try:
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip",
                "Content-Length": str(len(request_bytes))
            }

            original_size = len(request_bytes)

            # 大请求使用压缩
            if use_compression and len(request_bytes) >= COMPRESSION_THRESHOLD:
                request_bytes = gzip.compress(request_bytes)
                headers["Content-Encoding"] = "gzip"
                headers["Content-Length"] = str(len(request_bytes))

            conn.request("POST", jeb_path, request_bytes, headers)
            response = conn.getresponse()

            # 验证 HTTP 状态
            if response.status != 200:
                return json.dumps({
                    "error": f"HTTP {response.status}: {response.reason}"
                })

            raw_data = response.read()
            raw_size = len(raw_data)
            encoding = response.getheader("Content-Encoding")

            if encoding and "gzip" in encoding.lower():
                raw_data = gzip.decompress(raw_data)

            # 解析响应
            try:
                data = json.loads(raw_data.decode("UTF-8"))
            except UnicodeDecodeError:
                return json.dumps({"error": "Invalid response encoding"})
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON response"})

            # 检查 JSON-RPC 错误
            if "error" in data:
                err = data["error"]
                return json.dumps({"result": f"{str(err)}"})

            # 返回结果
            result = data.get("result")
            if result is None:
                return json.dumps({"result": "success"})
            try:
                return json.dumps({"result": result})
            except (TypeError, ValueError):
                return json.dumps({"result": str(result)})

        except socket.timeout:
            return json.dumps({"error": f"Request timeout after {timeout}s"})
        except http.client.HTTPException as e:
            return json.dumps({"error": f"HTTP error: {str(e)}"})
        finally:
            conn.close()

    except ConnectionRefusedError:
        return json.dumps({"error": f"Connection refused to {jeb_host}:{jeb_port}"})
    except OSError as e:
        return json.dumps({"error": f"Network error: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


def _jeb_call(method, *params) -> str:
    """统一的 JEB 调用函数，确保始终返回字符串"""
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
    """Open an APK or DEX file as a new project in JEB."""
    return _jeb_call('load_project', apk_or_dex_path)


@mcp.tool()
def has_projects():
    """Check if there are any projects currently loaded in JEB."""
    return _jeb_call('has_projects')


@mcp.tool()
def get_projects():
    """Retrieve a list of all projects currently loaded in JEB."""
    return _jeb_call('get_projects')


@mcp.tool()
def get_class_count():
    """Get the number of classes in the current project."""
    return _jeb_call('get_class_count')


@mcp.tool()
def get_class_by_index(index: str):
    """Get class information by index."""
    return _jeb_call('get_class_by_index', index)


@mcp.tool()
def get_current_project_info():
    """Retrieve detailed information about the current JEB session and loaded projects."""
    return _jeb_call('get_current_project_info')


@mcp.tool()
def get_method_smali_code(class_signature: str, method_name: str):
    """Get all Smali instructions for a specific method."""
    return _jeb_call('get_method_smali', class_signature, method_name)


@mcp.tool()
def ping():
    """Do a simple ping to check server is alive and running."""
    return _jeb_call("ping")


@mcp.tool()
def get_current_app_manifest():
    """Get the manifest of the currently loaded APK project in JEB."""
    return _jeb_call('get_app_manifest')


@mcp.tool()
def get_method_decompiled_code(class_name: str, method_name: str):
    """Get the decompiled code of the given method."""
    return _jeb_call('get_method_decompiled_code', class_name, method_name)


@mcp.tool()
def get_class_decompiled_code(class_signature: str):
    """Get the decompiled code of a class."""
    return _jeb_call('get_class_decompiled_code', class_signature)


@mcp.tool()
def get_method_callers(class_name: str, method_name: str):
    """Get all callers of the specified method."""
    return _jeb_call('get_method_callers', class_name, method_name)


@mcp.tool()
def get_method_overrides(method_signature: str):
    """Get the overrides of the given method."""
    return _jeb_call('get_method_overrides', method_signature)


@mcp.tool()
def get_field_callers(class_name: str, field_name: str):
    """Get the callers/references of the given field."""
    return _jeb_call('get_field_callers', class_name, field_name)


@mcp.tool()
def rename_class_name(class_name: str, new_name: str, ignore: bool = True):
    """Rename a class in the current APK project."""
    return _jeb_call('rename_class_name', class_name, new_name, ignore)


@mcp.tool()
def rename_method_name(class_name: str, method_name: str, new_name: str, ignore: bool = True):
    """Rename a method in the specified class."""
    return _jeb_call('rename_method_name', class_name, method_name, new_name, ignore)


@mcp.tool()
def rename_field_name(class_name: str, field_name: str, new_name: str, ignore: bool = True):
    """Rename a field in the specified class."""
    return _jeb_call('rename_field_name', class_name, field_name, new_name, ignore)


@mcp.tool()
def rename_local_variable(class_name: str, method_name: str, old_var_name: str, new_var_name: str):
    """Rename a local variable in the specified method."""
    return _jeb_call('rename_local_variable', class_name, method_name, old_var_name, new_var_name)


@mcp.tool()
def get_class_type_tree(class_signature: str, max_node_count: int = 16):
    """Build a hierarchical type tree for a class."""
    return _jeb_call('get_class_type_tree', class_signature, max_node_count)


@mcp.tool()
def get_class_superclass(class_signature: str):
    """Get the direct superclass of a specified class."""
    return _jeb_call('get_class_superclass', class_signature)


@mcp.tool()
def get_class_interfaces(class_signature: str):
    """Get all interfaces implemented by a specified class."""
    return _jeb_call('get_class_interfaces', class_signature)


@mcp.tool()
def parse_protobuf_class(class_signature: str):
    """Parse protobuf definition for a specific class."""
    return _jeb_call('parse_protobuf_class', class_signature)


@mcp.tool()
def get_class_methods(class_signature: str):
    """Get all methods of a specified class."""
    return _jeb_call('get_class_methods', class_signature)


@mcp.tool()
def get_class_fields(class_signature: str):
    """Get all fields of a specified class."""
    return _jeb_call('get_class_fields', class_signature)


@mcp.tool()
def is_class_renamed(class_signature: str):
    """Check if the specified class has been renamed."""
    return _jeb_call('is_class_renamed', class_signature)


@mcp.tool()
def is_method_renamed(class_signature: str, method_name: str):
    """Check if the specified method has been renamed."""
    return _jeb_call('is_method_renamed', class_signature, method_name)


@mcp.tool()
def is_field_renamed(class_signature: str, field_name: str):
    """Check if the specified field has been renamed."""
    return _jeb_call('is_field_renamed', class_signature, field_name)


@mcp.tool()
def is_package(package_name: str):
    """Check if the specified package exists."""
    return _jeb_call('is_package', package_name)


@mcp.tool()
def set_parameter_name(class_signature: str, method_name: str, index: int, name: str,
                       fail_on_conflict: bool = True, notify: bool = True):
    """Set a custom name for a parameter in the specified method."""
    return _jeb_call('set_parameter_name', class_signature, method_name, index, name,
                     fail_on_conflict, notify)


@mcp.tool()
def reset_parameter_name(class_signature: str, method_name: str, index: int, notify: bool = True):
    """Reset a parameter name to its default value."""
    return _jeb_call('reset_parameter_name', class_signature, method_name, index, notify)


@mcp.tool()
def find_class(class_signature: str):
    """Find a class in the currently loaded APK project."""
    return _jeb_call('find_class', class_signature)


@mcp.tool()
def find_method(class_signature: str, method_name: str):
    """Find a method in the currently loaded APK project."""
    return _jeb_call('find_method', class_signature, method_name)


@mcp.tool()
def find_field(class_signature: str, field_name: str):
    """Find a field in the currently loaded APK project."""
    return _jeb_call('find_field', class_signature, field_name)


@mcp.tool()
def get_live_artifact_ids():
    """Get a list of live artifact IDs currently loaded in JEB Pro."""
    return _jeb_call('get_live_artifact_ids')


@mcp.tool()
def switch_active_artifact(artifact_id):
    """Switch the active artifact in JEB Pro."""
    return _jeb_call('switch_active_artifact', artifact_id)


def main():
    parser = argparse.ArgumentParser(description="JEB Pro MCP Server (SSE/HTTP)")
    parser.add_argument("--transport", choices=["sse", "http", "stdio"],
                        default=os.environ.get("TRANSPORT", "stdio"),
                        help="MCP transport type: [sse, http, stdio] (default: stdio)")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"),
                        help="host server bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("PORT", "16162")),
                        help="host server bind port (default: 16162)")
    parser.add_argument("--jeb-host", default=os.environ.get("JEB_HOST", "127.0.0.1"))
    parser.add_argument("--jeb-port", type=int,
                        default=int(os.environ.get("JEB_PORT", "16161")))
    parser.add_argument("--jeb-path", default=os.environ.get("JEB_PATH", "/mcp"))
    parser.add_argument("--no-compression", action="store_true",
                        help="Disable GZIP compression for JSON-RPC requests")
    args = parser.parse_args()

    os.environ["JEB_HOST"] = args.jeb_host
    os.environ["JEB_PORT"] = str(args.jeb_port)
    os.environ["JEB_PATH"] = args.jeb_path

    global _use_compression
    _use_compression = not args.no_compression

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
