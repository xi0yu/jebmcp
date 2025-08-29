# -*- coding: utf-8 -*-
"""
JSON-RPC handler module - processes RPC requests and delegates to business logic
"""
import traceback
from functools import wraps
from .method_registry import get_method_definition, get_all_methods, validate_method_exists

def validate_params(param_count, param_names=None):
    """Decorator to validate method parameters"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, params):
            if len(params) < param_count:
                raise ValueError("{0} requires at least {1} parameter(s)".format(func.__name__, param_count))
            if param_names and len(params) > len(param_names):
                raise ValueError("{0} accepts at most {1} parameter(s)".format(func.__name__, len(param_names)))
            return func(self, params)
        return wrapper
    return decorator

class JSONRPCHandler(object):
    """Handles JSON-RPC requests and delegates to business logic"""
    
    def __init__(self, jeb_operations):
        self.jeb_operations = jeb_operations
    
    def handle_request(self, method, params):
        """Handle JSON-RPC method calls using method registry"""
        try:
            # 获取方法定义
            method_def = get_method_definition(method)
            if not method_def:
                raise ValueError("Unknown method: {0}".format(method))
            
            # 参数验证
            if len(params) < method_def.required_params:
                raise ValueError("{0} requires at least {1} parameter(s)".format(method, method_def.required_params))
            if method_def.param_names and len(params) > len(method_def.param_names):
                raise ValueError("{0} accepts at most {1} parameter(s)".format(method, len(method_def.param_names)))
            
            # 动态调用对应的处理函数
            handler_method = getattr(self, method_def.handler_method)
            return handler_method(params)
            
        except Exception as e:
            print("Error handling {0}: {1}".format(method, str(e)))
            traceback.print_exc()
            raise
    
    def _handle_ping(self, params):
        """Handle ping method"""
        return "pong"
    
    def _handle_get_manifest(self, params):
        """Handle get_manifest method"""
        return self.jeb_operations.get_manifest()
    
    @validate_params(1, ["method_signature"])
    def _handle_get_method_decompiled_code(self, params):
        """Handle get_method_decompiled_code method"""
        return self.jeb_operations.get_method_decompiled_code(params[0])
    
    @validate_params(1, ["class_signature"])
    def _handle_get_class_decompiled_code(self, params):
        """Handle get_class_decompiled_code method"""
        return self.jeb_operations.get_class_decompiled_code(params[0])
    
    @validate_params(1, ["method_signature"])
    def _handle_get_method_callers(self, params):
        """Handle get_method_callers method"""
        return self.jeb_operations.get_method_callers(params[0])
    
    @validate_params(1, ["method_signature"])
    def _handle_get_method_overrides(self, params):
        """Handle get_method_overrides method"""
        return self.jeb_operations.get_method_overrides(params[0])
    
    def get_supported_methods(self):
        """Get list of supported JSON-RPC methods with parameter info"""
        methods_info = []
        for method_def in get_all_methods():
            methods_info.append({
                "method": method_def.name,
                "required_params": method_def.required_params,
                "param_names": method_def.param_names,
                "param_types": method_def.param_types,
                "return_type": method_def.return_type,
                "description": method_def.description
            })
        return methods_info
    
    def get_method_info(self, method_name):
        """Get detailed information about a specific method"""
        method_def = get_method_definition(method_name)
        if not method_def:
            return None
        
        return {
            "method": method_def.name,
            "required_params": method_def.required_params,
            "param_names": method_def.param_names,
            "param_types": method_def.param_types,
            "return_type": method_def.return_type,
            "description": method_def.description
        }
    
    def get_method_signature(self, method_name):
        """Get method signature for documentation purposes"""
        method_def = get_method_definition(method_name)
        if not method_def:
            return None
        
        if method_def.required_params == 0:
            return "{0}() -> {1}".format(method_name, method_def.return_type)
        
        params_str = ", ".join(["{0}: {1}".format(name, type_) for name, type_ in zip(method_def.param_names, method_def.param_types)])
        return "{0}({1}) -> {2}".format(method_name, params_str, method_def.return_type)
