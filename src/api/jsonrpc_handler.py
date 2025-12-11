# -*- coding: utf-8 -*-
"""
JSON-RPC handler module - processes RPC requests and delegates to business logic
"""
import traceback
import inspect

class JSONRPCError(Exception):
    """Custom JSON-RPC error class"""
    def __init__(self, code, message, data=None):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        self.data = data

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
            "get_class_count": jeb_operations.get_class_count,
            "get_class_by_index": jeb_operations.get_class_by_index,
            "get_live_artifact_ids": jeb_operations.get_live_artifact_ids,
            "switch_active_artifact": jeb_operations.switch_active_artifact,
        }

    def handle_request(self, method, params):
        """Handle JSON-RPC method calls using direct method mapping"""
        try:
            # 检查方法是否存在
            if method not in self.method_handlers:
                raise JSONRPCError(-32601, "Method not found: {0}".format(method))

            # 直接调用方法，使用*params展开参数列表
            handler = self.method_handlers[method]
            if method == "ping":
                result = handler(params)
            else:
                result = handler(*params)

            return result

        except JSONRPCError:
            # 重新抛出JSON-RPC错误，让上层处理
            raise
        except Exception as e:
            print(u"Error handling {0}: {1}".format(method, str(e)))
            traceback.print_exc()
            raise JSONRPCError(-32603, "Internal error: {0}".format(str(e)))
