# -*- coding: utf-8 -*-
"""
Method registry configuration - defines all available JSON-RPC methods
"""
# Python 2.7 compatible version without type hints

class MethodDefinition(object):
    """Represents a method definition with metadata"""
    
    def __init__(self, name, handler_method, required_params=0, 
                 param_names=None, description="", 
                 param_types=None, return_type="any"):
        self.name = name
        self.handler_method = handler_method
        self.required_params = required_params
        self.param_names = param_names or []
        self.description = description
        self.param_types = param_types or []
        self.return_type = return_type

# 方法注册表配置
METHOD_REGISTRY = {
    "ping": MethodDefinition(
        name="ping",
        handler_method="_handle_ping",
        required_params=0,
        description="Simple ping to check server status",
        return_type="string"
    ),
    
    "get_manifest": MethodDefinition(
        name="get_manifest",
        handler_method="_handle_get_manifest",
        required_params=0,
        description="Get the manifest of the currently loaded APK project",
        return_type="string"
    ),
    
    "get_method_decompiled_code": MethodDefinition(
        name="get_method_decompiled_code",
        handler_method="_handle_get_method_decompiled_code",
        required_params=1,
        param_names=["method_signature"],
        param_types=["string"],
        description="Get decompiled code of a specific method",
        return_type="string"
    ),
    
    "get_class_decompiled_code": MethodDefinition(
        name="get_class_decompiled_code",
        handler_method="_handle_get_class_decompiled_code",
        required_params=1,
        param_names=["class_signature"],
        param_types=["string"],
        description="Get decompiled code of a specific class (supports auto JNI conversion)",
        return_type="string"
    ),
    
    "get_method_callers": MethodDefinition(
        name="get_method_callers",
        handler_method="_handle_get_method_callers",
        required_params=1,
        param_names=["method_signature"],
        param_types=["string"],
        description="Find all callers of a specific method",
        return_type="array"
    ),
    
    "get_method_overrides": MethodDefinition(
        name="get_method_overrides",
        handler_method="_handle_get_method_overrides",
        required_params=1,
        param_names=["method_signature"],
        param_types=["string"],
        description="Find all overrides of a specific method",
        return_type="array"
    ),
    
    "get_field_callers": MethodDefinition(
        name="get_field_callers",
        handler_method="_handle_get_field_callers",
        required_params=1,
        param_names=["field_signature"],
        param_types=["string"],
        description="Find all references/callers of a specific field",
        return_type="array"
    ),
    
    "set_class_name": MethodDefinition(
        name="set_class_name",
        handler_method="_handle_set_class_name",
        required_params=2,
        param_names=["class_name", "new_name"],
        param_types=["string", "string"],
        description="Set the name of a class in the current APK project. If new_name is provided, it will rename the class. If not provided, it will return current class info.",
        return_type="object"
    ),
    
    "set_method_name": MethodDefinition(
        name="set_method_name",
        handler_method="_handle_set_method_name",
        required_params=2,
        param_names=["class_name", "method_name", "new_name"],
        param_types=["string", "string", "string"],
        description="Set the name of a method in the specified class. If new_name is provided, it will rename the method. If not provided, it will return current method info.",
        return_type="object"
    ),
    
    "set_field_name": MethodDefinition(
        name="set_field_name",
        handler_method="_handle_set_field_name",
        required_params=2,
        param_names=["class_name", "field_name", "new_name"],
        param_types=["string", "string", "string"],
        description="Set the name of a field in the specified class. If new_name is provided, it will rename the field. If not provided, it will return current field info.",
        return_type="object"
    ),
    
    "check_status": MethodDefinition(
        name="check_status",
        handler_method="_handle_check_status",
        required_params=0,
        description="Get detailed status information about JEB and loaded projects including connection status, project count, APK/DEX details, and JEB version",
        return_type="object"
    ),
    
    "get_smali_instructions": MethodDefinition(
        name="get_smali_instructions",
        handler_method="_handle_get_smali_instructions",
        required_params=2,
        param_names=["class_signature", "method_name"],
        param_types=["string", "string"],
        description="Get all Smali instructions for a specific method in the given class. Supports auto JNI conversion for class signatures.",
        return_type="object"
    )
}

def get_method_definition(method_name):
    """Get method definition by name"""
    return METHOD_REGISTRY.get(method_name)

def get_all_methods():
    """Get all available methods"""
    return list(METHOD_REGISTRY.values())

def get_method_names():
    """Get list of all method names"""
    return list(METHOD_REGISTRY.keys())

def validate_method_exists(method_name):
    """Check if method exists"""
    return method_name in METHOD_REGISTRY
