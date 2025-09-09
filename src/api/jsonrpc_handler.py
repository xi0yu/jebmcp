# -*- coding: utf-8 -*-
"""
JSON-RPC handler module - processes RPC requests and delegates to business logic
"""
import traceback
import inspect

class JSONRPCHandler(object):
    """Handles JSON-RPC requests and delegates to business logic"""
    
    def __init__(self, jeb_operations):
        self.jeb_operations = jeb_operations
        
        # 直接映射到jeb_operations的方法，无需包装函数
        self.method_handlers = {
            "ping": lambda params: "pong",  # ping方法特殊处理
            "get_app_manifest": jeb_operations.get_app_manifest,
            "get_method_decompiled_code": jeb_operations.get_method_decompiled_code,
            "get_class_decompiled_code": jeb_operations.get_class_decompiled_code,
            "get_method_callers": jeb_operations.get_method_callers,
            "get_method_overrides": jeb_operations.get_method_overrides,
            "get_field_callers": jeb_operations.get_field_callers,
            "rename_class_name": jeb_operations.rename_class_name,
            "rename_method_name": jeb_operations.rename_method_name,
            "rename_field_name": jeb_operations.rename_field_name,
            "get_current_project_info": jeb_operations.get_current_project_info,
            "get_method_smali": jeb_operations.get_method_smali,
            "get_class_type_tree": jeb_operations.get_class_type_tree,
            "get_class_superclass": jeb_operations.get_class_superclass,
            "get_class_interfaces": jeb_operations.get_class_interfaces,
            "parse_protobuf_class": jeb_operations.parse_protobuf_class,
        }


    def _get_jeb_method_signature(self, method_name):
        if not hasattr(self.jeb_operations, method_name):
            return None
        
        jeb_method = getattr(self.jeb_operations, method_name)
        args, varargs, varkw, defaults = inspect.getargspec(jeb_method)
        
        if args and args[0] == 'self':
            args = args[1:]
        
        required_count = len(args) - (len(defaults) if defaults else 0)
        
        return {
            'required_params': required_count,
            'total_params': len(args),
            'param_names': args
        }
    
    def handle_request(self, method, params):
        """Handle JSON-RPC method calls using direct method mapping"""
        try:
            # 检查方法是否存在
            if method not in self.method_handlers:
                raise ValueError("Unknown method: {0}".format(method))
            
            # 自动参数验证（基于JEB操作方法的签名）
            sig_info = self._get_jeb_method_signature(method)
            if sig_info:
                if len(params) < sig_info['required_params']:
                    raise ValueError("{0} requires at least {1} parameter(s), got {2}".format(
                        method, sig_info['required_params'], len(params)))
                if len(params) > sig_info['total_params']:
                    raise ValueError("{0} accepts at most {1} parameter(s), got {2}".format(
                        method, sig_info['total_params'], len(params)))
            
            # 直接调用方法，使用*params展开参数列表
            handler = self.method_handlers[method]
            if method == "ping":
                return handler(params)  # ping方法特殊处理，接收params参数
            else:
                return handler(*params)  # 其他方法直接展开参数
            
        except Exception as e:
            print("Error handling {0}: {1}".format(method, str(e)))
            traceback.print_exc()
            raise
