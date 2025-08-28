# NOTE: This file has been automatically generated, do not modify!
# Architecture based on https://github.com/mrexodia/ida-pro-mcp (MIT License)
from typing import Annotated, Optional, TypedDict, Generic, TypeVar
from pydantic import Field

T = TypeVar("T")

@mcp.tool()
def ping() -> str:
    """Do a simple ping to check server is alive and running"""
    return make_jsonrpc_request('ping')

@mcp.tool()
def get_manifest() -> str:
    """Get the manifest of the currently loaded APK project in JEB"""
    return make_jsonrpc_request('get_manifest')

@mcp.tool()
def get_method_decompiled_code(method_signature: str) -> str:
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
def get_class_decompiled_code(class_signature: str) -> str:
    """Get the decompiled code of the given class in the currently loaded APK project
    Dex units use Java-style internal addresses to identify items:

    - package: Lcom/abc/
    - type: Lcom/abc/Foo;
    - method: Lcom/abc/Foo;->bar(I[JLjava/Lang/String;)V
    - field: Lcom/abc/Foo;->flag1:Z

    @param class_signature: The fully-qualified signature of the class to decompile, e.g. Lcom/abc/Foo;
    """
    return make_jsonrpc_request('get_class_decompiled_code', class_signature)

@mcp.tool()
def get_method_callers(method_signature: str) -> list[(str,str)]:
    """
    Get the callers of the given method in the currently loaded APK project
    """
    return make_jsonrpc_request('get_method_callers', method_signature)

@mcp.tool()
def get_method_overrides(method_signature: str) -> list[(str,str)]:
    """
    Get the overrides of the given method in the currently loaded APK project
    """
    return make_jsonrpc_request('get_method_overrides', method_signature)