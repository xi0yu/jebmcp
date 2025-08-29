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

def make_jsonrpc_request(method, *params):
    """Make a JSON-RPC request to the JEB plugin"""
    global jsonrpc_request_id
    conn = http.client.HTTPConnection("localhost", 16161)
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": list(params),
        "id": jsonrpc_request_id,
    }
    jsonrpc_request_id += 1

    try:
        conn.request("POST", "/mcp", json.dumps(request), {
            "Content-Type": "application/json"
        })
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        if "error" in data:
            error = data["error"]
            code = error["code"]
            message = error["message"]
            pretty = "JSON-RPC error {0}: {1}".format(code, message)
            if "data" in error:
                pretty += "\n" + error["data"]
            raise Exception(pretty)

        result = data["result"]
        # NOTE: LLMs do not respond well to empty responses
        if result is None:
            result = "success"
        return result
    except Exception:
        raise
    finally:
        conn.close()

@mcp.tool()
def check_connection():
    """Check if the JEB plugin is running"""
    try:
        metadata = make_jsonrpc_request("ping")
        return "Successfully connected to JEB Pro"
    except Exception as e:
        if sys.platform == "darwin":
            shortcut = "Ctrl+Option+M"
        else:
            shortcut = "Ctrl+Alt+M"
        return "Failed to connect to JEB Pro! Did you run Edit -> Scripts -> MCP ({0}) to start the server?".format(shortcut)

@mcp.tool()
def ping():
    """Do a simple ping to check server is alive and running"""
    return make_jsonrpc_request('ping')

@mcp.tool()
def get_manifest():
    """Get the manifest of the currently loaded APK project in JEB"""
    return make_jsonrpc_request('get_manifest')

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
    return make_jsonrpc_request('get_method_decompiled_code', method_signature)

@mcp.tool()
def get_class_decompiled_code(class_signature):
    """Get the decompiled code of a class in the current APK project.

    Input formats supported (auto-normalized to JNI signature):
    - Plain class name: e.g. "abjz"
    - Package + class with dots: e.g. "com.example.Foo"
    - JNI-style signature: e.g. "Lcom/example/Foo;"

    @param class_signature: Class identifier in any of the supported forms.
    """
    return make_jsonrpc_request('get_class_decompiled_code', class_signature)

@mcp.tool()
def get_method_callers(method_signature):
    """
    Get the callers of the given method in the currently loaded APK project
    """
    return make_jsonrpc_request('get_method_callers', method_signature)

@mcp.tool()
def get_method_overrides(method_signature):
    """
    Get the overrides of the given method in the currently loaded APK project
    """
    return make_jsonrpc_request('get_method_overrides', method_signature)

def main():
    argparse.ArgumentParser(description="JEB Pro MCP Server")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()