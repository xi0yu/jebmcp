# -*- coding: utf-8 -*-
"""
JEB operations module - handles all business logic for APK/DEX operations
"""
import hashlib
from com.pnfsoftware.jeb.core.units.code import ICodeItem
from com.pnfsoftware.jeb.core.units.code.android import IApkUnit, IDexUnit
from com.pnfsoftware.jeb.core.util import DecompilerHelper
from com.pnfsoftware.jeb.core.output.text import TextDocumentUtil
from com.pnfsoftware.jeb.core.actions import ActionXrefsData, Actions, ActionContext, ActionOverridesData

# Import signature utilities using absolute path for JEB compatibility
import sys
import os
from java.io import File
# Add the src directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from utils.signature_utils import convert_class_signature
from utils.protoParser import ProtoParser
class JebOperations(object):
    """Handles all JEB-specific operations for APK/DEX analysis"""
    
    def __init__(self, project_manager, ctx=None):
        self.project_manager = project_manager
        self.ctx = ctx

    def get_app_manifest(self):
        """Get the manifest of the currently loaded APK project in JEB"""
        project = self.project_manager.get_current_project()
        if project is None:
            return {"success": False, "error": "No project currently loaded in JEB"}
        
        # Find APK unit via project
        apk_unit = self.project_manager.find_apk_unit(project)
        if apk_unit is None:
            return {"success": False, "error": "No APK unit found in the current project"}
        
        man = apk_unit.getManifest()
        if man is None:
            return {"success": False, "error": "No manifest found in the APK unit"}
        
        doc = man.getFormatter().getPresentation(0).getDocument()
        text = TextDocumentUtil.getText(doc)
        return {"success": True, "manifest": text}
    
    def get_method_decompiled_code(self, class_name, method_name):
        """Get the decompiled code of the given method in the currently loaded APK project"""
        if not class_name or not method_name:
            return {"success": False, "error": "Both class name and method name are required"}

        project = self.project_manager.get_current_project()
        if project is None:
            return {"success": False, "error": "No project currently loaded in JEB"}
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            return {"success": False, "error": "No dex unit found in the current project"}
        
        # Find method
        method = self._find_method(dex_unit, class_name, method_name)
        if method is None:
            return {"success": False, "error": "Method not found: %s" % method_name}
        
        decomp = DecompilerHelper.getDecompiler(dex_unit)
        if not decomp:
            return {"success": False, "error": "Cannot acquire decompiler for unit"}

        if not decomp.decompileMethod(method.getSignature(True)):
            return {"success": False, "error": "Failed decompiling method"}

        text = decomp.getDecompiledMethodText(method.getSignature(True))
        return {"success": True, "decompiled_code": text, "method_signature": method.getSignature(True)}

    def _find_method(self, dex_unit, class_signature, method_name):
        """Find a method in the dex unit by class signature and method name"""
        if not class_signature or not method_name:
            return None
        
        # normalize class signature for JNI format before lookup
        normalized_signature = convert_class_signature(class_signature)
        clazz = dex_unit.getClass(normalized_signature)
        if clazz is None:
            return None
        
        # forEach method in the class
        for method in clazz.getMethods():
            if method.getName() == method_name:
                return method
        
        return None
    
    def get_class_decompiled_code(self, class_signature):
        """Get the decompiled code of a class in the current APK project"""
        if not class_signature:
            return {"success": False, "error": "Class signature is required"}

        project = self.project_manager.get_current_project()
        if project is None:
            return {"success": False, "error": "No project currently loaded in JEB"}

        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            return {"success": False, "error": "No dex unit found in the current project"}
        
        # normalize class signature for JNI format before lookup
        clazz = dex_unit.getClass(convert_class_signature(class_signature))
        if clazz is None:
            return {"success": False, "error": "Class not found: %s" % class_signature}
        
        decomp = DecompilerHelper.getDecompiler(dex_unit)
        if not decomp:
            return {"success": False, "error": "Cannot acquire decompiler for unit"}

        if not decomp.decompileClass(clazz.getSignature(True)):
            return {"success": False, "error": "Failed decompiling class"}

        text = decomp.getDecompiledClassText(clazz.getSignature(True))
        return {"success": True, "decompiled_code": text, "class_signature": clazz.getSignature(True)}
    
    def get_method_callers(self, class_name, method_name):
        """Get the callers of the given method in the currently loaded APK project"""
        if not class_name or not method_name:
            return {"success": False, "error": "Both class name and method name are required"}

        project = self.project_manager.get_current_project()
        if project is None:
            return {"success": False, "error": "No project currently loaded in JEB"}
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            return {"success": False, "error": "No dex unit found in the current project"}

        # Find method
        method = self._find_method(dex_unit, class_name, method_name)
        if method is None:
            return {"success": False, "error": "Method not found: %s" % method_name}
        
        action_xrefs_data = ActionXrefsData()
        action_context = ActionContext(dex_unit, Actions.QUERY_XREFS, method.getItemId(), None)
        ret = []
        if dex_unit.prepareExecution(action_context, action_xrefs_data):
            for i in range(action_xrefs_data.getAddresses().size()):
                ret.append((action_xrefs_data.getAddresses()[i], action_xrefs_data.getDetails()[i]))
        return {"success": True, "method_signature": method.getSignature(True), "callers": ret}
    
    def get_field_callers(self, class_name, field_name):
        """Get the callers/references of the given field in the currently loaded APK project"""
        if not class_name or not field_name:
            return {"success": False, "error": "Both class signature and method name are required"}

        project = self.project_manager.get_current_project()
        if project is None:
            return {"success": False, "error": "No project currently loaded in JEB"}
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            return {"success": False, "error": "No dex unit found in the current project"}
        
        # Get the class first
        dex_class = dex_unit.getClass(convert_class_signature(class_name))
        if dex_class is None:
            return {"success": False, "error": "Class not found: %s" % class_name}
        
        # Find the field in the class
        field = None
        for f in dex_class.getFields():
            if f.getName() == field_name:
                field = f
                break
        
        if field is None:
            return {"success": False, "error": "Field not found: %s" % field_name}

        # Use the same approach as method callers - query cross-references
        action_xrefs_data = ActionXrefsData()
        action_context = ActionContext(dex_unit, Actions.QUERY_XREFS, field.getItemId(), None)
        field_xrefs = []
        if dex_unit.prepareExecution(action_context, action_xrefs_data):
            for i in range(action_xrefs_data.getAddresses().size()):
                field_xrefs.append({
                    "address": str(action_xrefs_data.getAddresses()[i]),
                    "description": str(action_xrefs_data.getDetails()[i])
                })
        
        return {
            "success": True,
            "class_name": class_name,
            "field_name": field_name,
            "field_xrefs": field_xrefs
        }
    
    def get_method_overrides(self, method_signature):
        """Get the overrides of the given method in the currently loaded APK project"""
        if not method_signature:
            return {"success": False, "error": "Method signature is required"}

        project = self.project_manager.get_current_project()
        if project is None:
            return {"success": False, "error": "No project currently loaded in JEB"}
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            return {"success": False, "error": "No dex unit found in the current project"}
        
        ret = []
        method = dex_unit.getMethod(method_signature)
        if method is None:
            return {"success": False, "error": "Method not found: %s" % method_signature}
        
        data = ActionOverridesData()
        action_context = ActionContext(dex_unit, Actions.QUERY_OVERRIDES, method.getItemId(), None)
        if dex_unit.prepareExecution(action_context, data):
            for i in range(data.getAddresses().size()):
                ret.append((data.getAddresses()[i], data.getDetails()[i]))
        return {"success": True, "method_signature": method_signature, "overrides": ret}
    
    def rename_class_name(self, class_name, new_name):
        """Set the name of a class in the current APK project"""
        if not class_name:
            return {"success": False, "error": "class name is required"}
        
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}
            
            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No dex unit found in the current project"}
            
            # Normalize class signature for JNI format
            dex_class = dex_unit.getClass(convert_class_signature(class_name))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_name}
            
            if not dex_class.setName(new_name):
                return  {"success": False, "error": "Failed to set class name: %s" % new_name}
            
            return {
                "success": True, 
                "new_class_name": new_name,
                "message": "Class name retrieved successfully"
            }
        except Exception as e:
            return {"success": False, "error": "Failed to set class name. exception: %s" % str(e)}
    
    def rename_method_name(self, class_name, method_name, new_name):
        """Set the name of a method in the specified class"""
        if not class_name or not method_name:
            return {"success": False, "error": "Both class signature and method name are required"}
        
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}
            
            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No dex unit found in the current project"}
            
            # Normalize class signature for JNI format
            clazz = dex_unit.getClass(convert_class_signature(class_name))
            if clazz is None:
                return {"success": False, "error": "Class not found: %s" % class_name}
            
            # Find method by name in the class
            is_renamed = False
            for method in clazz.getMethods():
                if method.getName() == method_name:
                    is_renamed = method.setName(new_name)
                    break
            
            if not is_renamed:
                return {"success": False, "error": "Rename failed for method '%s' in class %s" % (method_name, class_name)}
            
            return {
                "success": True,
                "class_name": class_name,
                "new_method_name": new_name,
                "message": "Method rename successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": "Failed to rename method '%s' in class %s: %s" % (method_name, class_name, str(e))}
    
    def rename_field_name(self, class_name, field_name, new_name):
        """Set the name of a field in the specified class"""
        if not class_name or not field_name:
            return {"success": False, "error": "Both class signature and field name are required"}

        if new_name is None:
            return {"success": False, "error": "New name is required"}
        
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}
            
            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No dex unit found in the current project"}
            
            # Normalize class signature for JNI format
            clazz = dex_unit.getClass(convert_class_signature(class_name))
            if clazz is None:
                return {"success": False, "error": "Class not found: %s" % class_name}
            
            # Find field by name in the class
            is_renamed = False
            for field in clazz.getFields():
                if field.getName() == field_name:
                    is_renamed = field.setName(new_name)
                    break
            
            if not is_renamed:
                return {"success": False, "error": "Rename failed for field '%s' in class %s" % (field_name, class_name)}
            
            return {
                "success": True,
                "class_name": class_name,
                "new_field_name": new_name,
                "message": "Field found successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": "Failed to rename field '%s' in class %s: %s" % (field_name, class_name, str(e))}
    
    def get_method_smali(self, class_signature, method_name):
        """Get all Smali instructions for a specific method in the given class"""
        if not class_signature or not method_name:
            return {"success": False, "error": "Both class signature and method name are required"}
        
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}
            
            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No dex unit found in the current project"}
            
            # Normalize class signature for JNI format
            normalized_signature = convert_class_signature(class_signature)
            clazz = dex_unit.getClass(normalized_signature)
            if clazz is None:
                return {"success": False, "error": "Class not found: %s" % normalized_signature}
            
            # Find method by name in the class
            methods = clazz.getMethods()
            found_methods = []
            
            for method in methods:
                if method.getName() == method_name:
                    # Get Smali instructions for this method
                    smali_instructions = self._get_method_smali_instructions(method)
                    
                    found_methods.append({
                        "signature": method.getSignature(True),
                        "name": method.getName(),
                        "smali_instructions": smali_instructions
                    })
            
            if not found_methods:
                return {"success": False, "error": "Method '%s' not found in class %s" % (method_name, normalized_signature)}
            
            return {
                "success": True,
                "class_signature": normalized_signature,
                "method_name": method_name,
                "methods": found_methods,
                "message": "Smali instructions retrieved successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": "Failed to get Smali instructions: %s" % str(e)}
    
    def _get_method_smali_instructions(self, method):
        """Get Smali instructions for a specific method"""
        try:
            instructions = []
            
            # Get all instructions
            instruction_count = method.getInstructions().size()
            for i in range(instruction_count):
                instruction = method.getInstructions().getInstruction(i)
                if instruction is not None:
                    # Get instruction details
                    instruction_info = {
                        "index": i,
                        "address": instruction.getAddress(),
                        "mnemonic": instruction.getMnemonic(),
                        "operands": self._get_instruction_operands(instruction),
                        "raw_text": str(instruction)
                    }
                    instructions.append(instruction_info)
            
            return instructions
            
        except Exception as e:
            print("Error getting Smali instructions: %s" % str(e))
            return []
    
    def _get_instruction_operands(self, instruction):
        """Get operands for a specific instruction"""
        try:
            operands = []
            
            # Get operand count
            operand_count = instruction.getOperandCount()
            for i in range(operand_count):
                operand = instruction.getOperand(i)
                if operand is not None:
                    operand_info = {
                        "index": i,
                        "type": operand.getClass().getSimpleName(),
                        "value": str(operand),
                        "text": operand.toString()
                    }
                    operands.append(operand_info)
            
            return operands
            
        except Exception as e:
            print("Error getting instruction operands: %s" % str(e))
            return []
    
    def get_class_type_tree(self, class_signature, max_node_count):
        """Get the type tree for a given class signature
        
        Args:
            class_signature (str): The class signature to analyze
            max_node_count (int): Maximum node count to traverse
            
        Returns:
            dict: Success status and type tree data
        """
        project = self.project_manager.get_current_project()
        if project is None:
            return {"success": False, "error": "No project currently loaded in JEB"}
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            return {"success": False, "error": "No DEX unit found in the current project"}
        
        try:
            # Find code node
            code_node = dex_unit.getTypeHierarchy(convert_class_signature(class_signature), max_node_count, False)
            if code_node is None:
                return {"success": False, "error": "Class Node not found: %s" % class_signature}

            # Build type tree
            type_tree = self._build_type_tree(code_node)
            
            return {
                "success": True,
                "type_tree": type_tree
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "Failed to get type tree: %s" % str(e)
            }
    
    def _build_type_tree(self, node):
        """递归构建 dict 结构"""
        if node is None:
            return None

        obj = node.getObject()
        node_dict = {
            "name": obj.getName() if obj else "<?>",
            "signature": obj.getSignature(True) if obj else "",
            "children": []
        }

        if node.hasChildren():
            for child in node.getChildren():
                node_dict["children"].append(self._build_type_tree(child))

        return node_dict

    def get_current_project_info(self):
        """Get detailed status information about JEB and loaded projects"""
        try:
            # Check MCP to JEB connection
            connection_status = "connected"
            project_info = "No project currently loaded in JEB"
            project = self.project_manager.get_current_project()
            if project is not None:
                try:
                    project_info = self.project_manager.get_project_details(project)
                except Exception as e:
                    print("Error getting project: %s" % str(e))
            
            # Get JEB version info (optional)
            jeb_version = self.ctx.getSoftwareVersion().toString()
            
            return {
                "connection": {
                    "status": connection_status,
                    "message": "MCP to JEB connection status"
                },
                "project_info": project_info,
                "jeb_version": jeb_version
            }
            
        except Exception as e:
            return {
                "connection": {
                    "status": "error",
                    "message": "Failed to check status: %s" % str(e)
                },
                "project_info": None,
                "jeb_version": None
            }
    

    def get_class_superclass(self, class_signature):
        """Get the superclass of a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains superclass information or error details
        """
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}

            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No DEX unit found in the current project"}

            dex_class = dex_unit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}

            return {
                "success": True,
                "superclass": dex_class.getSupertypeSignature(True)
            }
        except Exception as e:
            return {"error": "Failed to get superclass: %s" % str(e)}

    def get_class_interfaces(self, class_signature):
        """Get all interfaces implemented by a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains interfaces information or error details
        """
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}

            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No DEX unit found in the current project"}

            dex_class = dex_unit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}

            interface_signatures = []
            for clazz in dex_class.getInterfaceSignatures(True):
                interface_signatures.append(clazz)

            return {
                "success": True,
                "interfaces": interface_signatures
            }
        except Exception as e:
            return {"error": "Failed to get class interfaces: %s" % str(e)}

    def parse_protobuf_class(self, class_signature):
        """解析指定类的protobuf定义"""
        if not class_signature:
            return {"success": False, "error": "Class signature is required"}

        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}

            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No dex unit found in the current project"}

            # 创建protobuf解析器
            parser = ProtoParser(dex_unit)
            result = parser.parse_class(class_signature)

            return result

        except Exception as e:
            return {"success": False, "error": "Failed to parse protobuf class: %s" % str(e)}

    def get_class_methods(self, class_signature):
        """Get all methods of a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains methods information or error details
        """
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}

            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No DEX unit found in the current project"}

            dex_class = dex_unit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}

            methods = []
            for method in dex_class.getMethods():
                method_info = {
                    "name": method.getName(),
                    "signature": method.getSignature(True),
                    "return_type": method.getReturnType().getSignature() if method.getReturnType() else "void",
                    "parameters": [],
                    "access_flags": GenericFlagParser.parse_flags(method.getGenericFlags())
                }
                
                # Get parameter types
                param_types = method.getParameterTypes()
                if param_types:
                    for param_type in param_types:
                        method_info["parameters"].append(param_type.getSignature(True))
                
                methods.append(method_info)

            return {
                "success": True,
                "class_signature": class_signature,
                "methods": methods,
                "method_count": len(methods)
            }
            
        except Exception as e:
            return {"success": False, "error": "Failed to get class methods: %s" % str(e)}

    def get_class_fields(self, class_signature):
        """Get all fields of a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains fields information or error details
        """
        try:
            project = self.project_manager.get_current_project()
            if project is None:
                return {"success": False, "error": "No project currently loaded in JEB"}

            dex_unit = self.project_manager.find_dex_unit(project)
            if dex_unit is None:
                return {"success": False, "error": "No DEX unit found in the current project"}

            dex_class = dex_unit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}

            fields = []
            for field in dex_class.getFields():
                field_info = {
                    "name": field.getName(),
                    "signature": field.getSignature(True),
                    "type": field.getType().getSignature(True) if field.getType() else "unknown",
                    "access_flags": GenericFlagParser.parse_flags(field.getGenericFlags())
                }
                
                # Get initial value if available
                try:
                    initial_value = field.getInitialValue()
                    if initial_value is not None:
                        field_info["initial_value"] = str(initial_value)
                    else:
                        field_info["initial_value"] = None
                except:
                    field_info["initial_value"] = None
                
                fields.append(field_info)

            return {
                "success": True,
                "class_signature": class_signature,
                "fields": fields,
                "field_count": len(fields)
            }
            
        except Exception as e:
            return {"success": False, "error": "Failed to get class fields: %s" % str(e)}

    def load_project(self, file_path):
        """Open a new project from file path
        
        Args:
            file_path (str): Path to the APK/DEX file to open
            
        Returns:
            dict: Success status and project information
        """
        return self.project_manager.load_project(file_path)
    
    
    def has_projects(self):
        """Check if there are any projects loaded in JEB"""
        return self.project_manager.has_projects()
    
    def get_projects(self):
        """Get information about all loaded projects in JEB"""
        return self.project_manager.get_projects()
    
    def unload_projects(self):
        """Unload all projects from JEB"""
        return self.project_manager.unload_projects()

class GenericFlagParser:
    """解析 ICodeItem.getGenericFlags() 返回值，将其转换为可读标志列表"""

    FLAGS = {
        ICodeItem.FLAG_PUBLIC:        "PUBLIC",
        ICodeItem.FLAG_PRIVATE:       "PRIVATE",
        ICodeItem.FLAG_PROTECTED:     "PROTECTED",
        ICodeItem.FLAG_STATIC:        "STATIC",
        ICodeItem.FLAG_FINAL:         "FINAL",
        ICodeItem.FLAG_SYNCHRONIZED:  "SYNCHRONIZED",
        ICodeItem.FLAG_VOLATILE:      "VOLATILE",
        ICodeItem.FLAG_TRANSIENT:     "TRANSIENT",
        ICodeItem.FLAG_NATIVE:        "NATIVE",
        ICodeItem.FLAG_INTERFACE:     "INTERFACE",
        ICodeItem.FLAG_ABSTRACT:      "ABSTRACT",
        ICodeItem.FLAG_STRICT:        "STRICT",
        ICodeItem.FLAG_SYNTHETIC:     "SYNTHETIC",
        ICodeItem.FLAG_ANNOTATION:    "ANNOTATION",
        ICodeItem.FLAG_ENUM:          "ENUM",
        ICodeItem.FLAG_CONSTRUCTOR:   "CONSTRUCTOR",
        ICodeItem.FLAG_DECLARED_SYNCHRONIZED: "DECLARED_SYNCHRONIZED",
        ICodeItem.FLAG_INNER:         "INNER",
        ICodeItem.FLAG_ANONYMOUS:     "ANONYMOUS",
        ICodeItem.FLAG_ARTIFICIAL:    "ARTIFICIAL",
        ICodeItem.FLAG_INTERNAL:      "INTERNAL",
        ICodeItem.FLAG_VARARGS:       "VARARGS",
        ICodeItem.FLAG_VIRTUAL:       "VIRTUAL",
        ICodeItem.FLAG_BRIDGE:        "BRIDGE",
        ICodeItem.FLAG_DESTRUCTOR:    "DESTRUCTOR",
    }

    @classmethod
    def parse_flags(cls, value):
        """
        解析 getGenericFlags() 的结果，返回值与所含标志列表。
        :param code_item: 实现 ICodeItem（如 ICodeClass、ICodeMethod 等）
        :return: dict，包含 'value'（原始整数标志）和 'flags'（可读标志名列表）
        """
        active = [name for bit, name in cls.FLAGS.items() if value & bit]
        return {"value": value, "flags": active}
