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
            "find_class": jeb_operations.find_class,
            "find_method": jeb_operations.find_method,
            "find_field": jeb_operations.find_field,
            "get_app_manifest": jeb_operations.get_app_manifest,
            "get_method_decompiled_code": jeb_operations.get_method_decompiled_code,
            "get_class_decompiled_code": jeb_operations.get_class_decompiled_code,
            "get_method_callers": jeb_operations.get_method_callers,
            "get_method_overrides": jeb_operations.get_method_overrides,
            "get_field_callers": jeb_operations.get_field_callers,
            "is_class_renamed": jeb_operations.is_class_renamed,
            "is_method_renamed": jeb_operations.is_method_renamed,
            "is_field_renamed": jeb_operations.is_field_renamed,
            "is_package": jeb_operations.is_package,
            "rename_class_name": jeb_operations.rename_class_name,
            "rename_method_name": jeb_operations.rename_method_name,
            "rename_field_name": jeb_operations.rename_field_name,
            "set_parameter_name": jeb_operations.set_parameter_name,
            "get_current_project_info": jeb_operations.get_current_project_info,
            "get_method_smali": jeb_operations.get_method_smali,
            "get_class_type_tree": jeb_operations.get_class_type_tree,
            "get_class_superclass": jeb_operations.get_class_superclass,
            "get_class_interfaces": jeb_operations.get_class_interfaces,
            "parse_protobuf_class": jeb_operations.parse_protobuf_class,
            "get_class_methods": jeb_operations.get_class_methods,
            "get_class_fields": jeb_operations.get_class_fields,
            "load_project": jeb_operations.load_project,
            "has_projects": jeb_operations.has_projects,
            "get_projects": jeb_operations.get_projects,
            "get_live_artifact_ids": jeb_operations.get_live_artifact_ids,
            "switch_active_artifact": jeb_operations.switch_active_artifact,
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
            print(u"Error handling {0}: {1}".format(method, str(e)))
            traceback.print_exc()
            raise
