# -*- coding: utf-8 -*-
"""
JEB operations module - handles all business logic for APK/DEX operations
"""
import hashlib
import json
from com.pnfsoftware.jeb.core.units.code import ICodeItem
from com.pnfsoftware.jeb.core.units.code.android import IApkUnit, IDexUnit
from com.pnfsoftware.jeb.core.util import DecompilerHelper
from com.pnfsoftware.jeb.core.output.text import TextDocumentUtil
from com.pnfsoftware.jeb.core.actions import ActionXrefsData, Actions, ActionContext, ActionOverridesData

# Import signature utilities using absolute path for JEB compatibility
import sys
import os
import traceback
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

    def _extract_last_segment(self, new_name):
        if "." in new_name:
            return new_name.split(".")[-1]
        return new_name

    def get_app_manifest(self):
        """Get the manifest of the currently loaded APK project in JEB"""
        apk_unit, err = self.project_manager.get_current_apk_unit()
        if err: return err
        
        man = apk_unit.getManifest()
        if man is None:
            return {"success": False, "error": "No manifest found in the APK unit"}
        
        doc = man.getFormatter().getPresentation(0).getDocument()
        text = TextDocumentUtil.getText(doc)
        return {"success": True, "manifest": text}
    
    def get_method_decompiled_code(self, class_signature, method_name):
        """Get the decompiled code of the given method in the currently loaded APK project"""

        dexUnit, err = self.project_manager.get_current_dex_unit()
        if err: return err

        # Find method
        method = self._find_method(dexUnit, class_signature, method_name)
        if method is None:
            return {"success": False, "error": "Method not found: %s" % method_name}
        
        decomp = DecompilerHelper.getDecompiler(dexUnit)
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
            if method.getName(True) == method_name or method.getName(False) == method_name:
                return method
        
        return None
    def _find_field(self, dex_unit, class_signature, field_name):
        """Find a field in the dex unit by class signature and field name"""
        if not class_signature or not field_name:
            return None

        # normalize class signature for JNI format before lookup
        normalized_signature = convert_class_signature(class_signature)
        clazz = dex_unit.getClass(normalized_signature)
        if clazz is None:
            return None

        # forEach field in the class
        for field in clazz.getFields():
            if field.getName(True) == field_name or field.getName(False) == field_name:
                return field

        return None

    def get_class_decompiled_code(self, class_signature):
        """Get the decompiled code of a class in the current APK project"""
        if not class_signature:
            return {"success": False, "error": "Class signature is required"}

        dexUnit, err = self.project_manager.get_current_dex_unit()
        if err: return err
        
        # normalize class signature for JNI format before lookup
        clazz = dexUnit.getClass(convert_class_signature(class_signature))
        if clazz is None:
            return {"success": False, "error": "Class not found: %s" % class_signature}
        
        decomp = DecompilerHelper.getDecompiler(dexUnit)
        if not decomp:
            return {"success": False, "error": "Cannot acquire decompiler for unit"}

        if not decomp.decompileClass(clazz.getSignature(True)):
            return {"success": False, "error": "Failed decompiling class"}

        text = decomp.getDecompiledClassText(clazz.getSignature(True))
        return {"success": True, "decompiled_code": text, "class_signature": clazz.getSignature(True)}
    
    def get_method_callers(self, class_signature, method_name):
        """Get the callers of the given method in the currently loaded APK project"""
        if not class_signature or not method_name:
            return {"success": False, "error": "Both class_signature and method_name are required"}

        dexUnit, err = self.project_manager.get_current_dex_unit()
        if err: return err

        # Find method
        method = self._find_method(dexUnit, class_signature, method_name)
        if method is None:
            return {"success": False, "error": "Method not found: %s" % method_name}
        
        action_xrefs_data = ActionXrefsData()
        action_context = ActionContext(dexUnit, Actions.QUERY_XREFS, method.getItemId(), None)
        ret = []
        if dexUnit.prepareExecution(action_context, action_xrefs_data):
            for i in range(action_xrefs_data.getAddresses().size()):
                ret.append((action_xrefs_data.getAddresses()[i], action_xrefs_data.getDetails()[i]))
        return {"success": True, "method_signature": method.getSignature(True), "callers": ret}
    
    def get_field_callers(self, class_signature, field_name):
        """Get the callers/references of the given field in the currently loaded APK project"""
        if not class_signature or not field_name:
            return {"success": False, "error": "Both class_signature and field_name are required"}
        
        dexUnit, err = self.project_manager.get_current_dex_unit()
        if err: return err

        field = self._find_field(dexUnit, class_signature, field_name)
        if field is None:
            return {"success": False, "error": "Field not found: %s" % field_name}

        # Use the same approach as method callers - query cross-references
        action_xrefs_data = ActionXrefsData()
        action_context = ActionContext(dexUnit, Actions.QUERY_XREFS, field.getItemId(), None)
        field_xrefs = []
        if dexUnit.prepareExecution(action_context, action_xrefs_data):
            for i in range(action_xrefs_data.getAddresses().size()):
                field_xrefs.append({
                    "address": str(action_xrefs_data.getAddresses()[i]),
                    "description": str(action_xrefs_data.getDetails()[i])
                })
        
        return {
            "success": True,
            "class_name": class_signature,
            "field_name": field_name,
            "field_xrefs": field_xrefs
        }
    
    def get_method_overrides(self, method_signature):
        """Get the overrides of the given method in the currently loaded APK project"""
        if not method_signature:
            return {"success": False, "error": "method_signature is required"}
        
        dexUnit, err = self.project_manager.get_current_dex_unit()
        if err: return err
        
        ret = []
        method = dexUnit.getMethod(method_signature)
        if method is None:
            return {"success": False, "error": "Method not found: %s" % method_signature}
        
        data = ActionOverridesData()
        action_context = ActionContext(dexUnit, Actions.QUERY_OVERRIDES, method.getItemId(), None)
        if dexUnit.prepareExecution(action_context, data):
            for i in range(data.getAddresses().size()):
                ret.append((data.getAddresses()[i], data.getDetails()[i]))
        return {"success": True, "method_signature": method_signature, "overrides": ret}
    
    def rename_class_name(self, class_name, new_name, ignore):
        """Set the name of a class in the current APK project"""
        if not class_name or not new_name:
            return {"success": False, "error": "Boat class_name and new_name is required"}
        
        try:            
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err
            
            # Normalize class signature for JNI format
            dex_class = dexUnit.getClass(convert_class_signature(class_name))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_name}
            
            old_name = dex_class.getName(True)
            new_name = self._extract_last_segment(new_name)

            if old_name == new_name:
                return {"success": True, "message": "Class name already set to %s" % new_name}

            if not dex_class.setName(new_name):
                return  {"success": False, "error": "Failed to set class name: %s" % new_name}
            
            return {
                "success": True, 
                "new_class_name": new_name,
                "message": "Renaming succeeded"
            }
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "Failed to set class name for '%s': %s. "
                    "You may try updating JEB or this plugin to the latest version to resolve potential API changes."
                    % (class_name, str(e))
                ),
                "traceback": traceback.format_exc()
            }
    
    def rename_method_name(self, class_name, method_name, new_name, ignore):
        """Set the name of a method in the specified class"""
        if not class_name or not method_name:
            return {"success": False, "error": "Both class signature and method name are required"}

        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            # Find method by name in the class
            finded_method = self._find_method(dexUnit, class_name, method_name)
            if not finded_method:
                return {"success": False, "error": "Method not found: %s" % method_name}
            
            old_name = finded_method.getName(True)
            new_name = self._extract_last_segment(new_name)

            if old_name == new_name:
                return {"success": True, "message": "Method name already set to %s" % new_name}

            if not finded_method.setName(new_name):
                return {"success": False, "error": "Rename failed for method '%s' in class %s" % (method_name, class_name)}

            return {
                "success": True,
                "class_name": class_name,
                "new_method_name": new_name,
                "message": "Renaming succeeded"
            }

        except Exception as e:
            return {
                "success": False,
                "error": (
                    "Failed to rename method '%s' in class '%s': %s. "
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                    % (method_name, class_name, str(e))
                ),
                "traceback": traceback.format_exc()
            }
    
    def rename_field_name(self, class_name, field_name, new_name, ignore):
        """Set the name of a field in the specified class"""
        if not class_name or not field_name:
            return {"success": False, "error": "Both class signature and field name are required"}

        if new_name is None:
            return {"success": False, "error": "New name is required"}
        
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err
            
            # Normalize class signature for JNI format
            clazz = dexUnit.getClass(convert_class_signature(class_name))
            if clazz is None:
                return {"success": False, "error": "Class not found: %s" % class_name}
            
            # Find field by name in the class
            finded_field = self._find_field(dexUnit, class_name, field_name)
            if not finded_field:
                return {"success": False, "error": "Field not found: %s" % field_name}

            old_name = finded_field.getName(True)
            new_name = self._extract_last_segment(new_name)

            if old_name == new_name:
                return {"success": True, "message": "Field name already set to %s" % new_name}

            if not finded_field.setName(new_name):
                return {"success": False, "error": "Rename failed for field '%s' in class %s" % (field_name, class_name)}
            
            return {
                "success": True,
                "class_name": class_name,
                "new_field_name": new_name,
                "message": "Field found successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "Exception occurred while renaming field '{field_name}' in class '{class_name}' to '{new_name}': {exc}\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(field_name=field_name, class_name=class_name, new_name=new_name, exc=str(e)),
                "traceback": traceback.format_exc()
            }

    
    def get_method_smali(self, class_signature, method_name):
        """Get all Smali instructions for a specific method in the given class"""
        if not class_signature or not method_name:
            return {"success": False, "error": "Both class signature and method name are required"}
        
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err
            
            found_method = self._find_method(dexUnit, class_signature, method_name)
            if found_method is None:
                return {"success": False, "error": "Method not found: %s" % method_name}

            smali_instructions = [ins.format(None) for ins in (found_method.getInstructions() or []) if ins]
            return {
                "success": True,
                "class_signature": class_signature,
                "method_name": method_name,
                "smali_instructions": smali_instructions,
                "message": "Smali instructions retrieved successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }
    def get_class_type_tree(self, class_signature, max_node_count):
        """Get the type tree for a given class signature
        
        Args:
            class_signature (str): The class signature to analyze
            max_node_count (int): Maximum node count to traverse
            
        Returns:
            dict: Success status and type tree data
        """
        dexUnit, err = self.project_manager.get_current_dex_unit()
        if err: return err
        
        try:
            # Find code node
            code_node = dexUnit.getTypeHierarchy(convert_class_signature(class_signature), max_node_count, False)
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
            if self.ctx is None:
                return {
                    "success": False,
                    "error": "JEB context is not available"
                }

            jeb_version = self.ctx.getSoftwareVersion().toString()

            current_artifact, err = self.project_manager.get_current_artifact()
            if err: return err

            current_artifact_id = current_artifact.getMainUnit().getName() if current_artifact else "N/A"
            return {
                "success": True,
                "current_artifact_id": current_artifact_id,
                "project_info": self.project_manager.get_project_details(),
                "jeb_version": jeb_version
            }

        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }
    

    def get_class_superclass(self, class_signature):
        """Get the superclass of a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains superclass information or error details
        """
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dex_class = dexUnit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}

            return {
                "success": True,
                "superclass": dex_class.getSupertypeSignature(True)
            }
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }

    def get_class_interfaces(self, class_signature):
        """Get all interfaces implemented by a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains interfaces information or error details
        """
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dex_class = dexUnit.getClass(convert_class_signature(class_signature))
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
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }

    def parse_protobuf_class(self, class_signature):
        """解析指定类的protobuf定义"""
        if not class_signature:
            return {"success": False, "error": "Class signature is required"}

        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            # 创建protobuf解析器
            parser = ProtoParser(dexUnit)
            result = parser.parse_class(class_signature)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }

    def get_class_methods(self, class_signature):
        """Get all methods of a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains methods information or error details
        """
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dex_class = dexUnit.getClass(convert_class_signature(class_signature))
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
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }

    def get_class_fields(self, class_signature):
        """Get all fields of a given class

        Args:
            class_signature (str): The class signature to analyze

        Returns:
            dict: Contains fields information or error details
        """
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dex_class = dexUnit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}

            fields = []
            for field in dex_class.getFields():
                field_info = {
                    "name": field.getName(),
                    "signature": field.getSignature(True),
                    "type": field.getFieldType().getSignature(True) if field.getFieldType() else "unknown",
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
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }

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
        try:            
            return {"success": True, "projects": self.project_manager.get_project_details()}
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }
    
    def unload_projects(self):
        """Unload all projects from JEB"""
        return self.project_manager.unload_projects()

    def is_class_renamed(self, class_signature):
        """
        Check if the specified class has been renamed in the current project.
        """
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dex_class = dexUnit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}
            
            return {
                "success": True,
                "renamed": dex_class.isRenamed()
            }
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }


    def is_method_renamed(self, class_signature, method_signature):
        """
        Check if the specified method has been renamed in the current project.
        """
        try:
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dex_class = dexUnit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}


            for method in dex_class.getMethods():
                if method_signature in method.getSignature(True):
                    return {
                        "success": True,
                        "renamed": method.isRenamed()
                    }

            return {"success": False, "error": "Method not found: %s" % method_signature}
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }


    def is_field_renamed(self, class_signature, field_signature):
        """
        Check if the specified field has been renamed in the current project.
        """
        try: 
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dex_class = dexUnit.getClass(convert_class_signature(class_signature))
            if dex_class is None:
                return {"success": False, "error": "Class not found: %s" % class_signature}

            
            for field in dex_class.getFields():
                if field_signature in field.getSignature(True):
                    return {
                        "success": True,
                        "renamed": field.isRenamed()
                    }
            
            return {"success": False, "error": "Field not found: %s" % field_signature}
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }

    def is_package(self, package_name):
        """
        Check if the specified package_name is a package.
        """
        try:
            dexUnit = self.project_manager.get_current_dex_unit()
            if dexUnit is None:
                return {"success": False, "error": "No DEX unit currently loaded in JEB"}
            
            isPackage = False
            dexPackage = dexUnit.getPackage(package_name)
            if dexPackage is not None:
                isPackage = True
            
            return {"success": True, "is_package": isPackage}
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }


    def set_parameter_name(self, class_signature, method_name, index, name, fail_on_conflict = True, notify = True):
        """
        Set the name of a parameter in the specified method of the current project.
        """
        try: 
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dexMethod = self._find_method(dexUnit, class_signature, method_name)
            if dexMethod is None:
                return {"success": False, "error": "Method not found: %s" % method_name}

            if index < 0:
                return {"success": False, "error": "Parameter index cannot be negative: %d" % index}
            
            dexMethodParameterLength = len(dexMethod.getParameterTypes())
            if index >= dexMethodParameterLength:
                return {"success": False, "error": "Parameter index out of range: %d" % index}
            
            result = dexMethod.setParameterName(index, name, fail_on_conflict, notify)
            if not result:
                return {"success": False, "error": "Failed to set parameter name"}
            
            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }
    
    def find_class(self, class_signature):
        """Find a class by its signature in the current project"""
        try: 
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err
            
            dexClass = dexUnit.getClass(convert_class_signature(class_signature))
            if dexClass is None: 
                return {"success": False, "error": "Class not found: %s" % class_signature}

            return {
                "success": True, 
                "current_name": dexClass.getName(True),
                "original_name": dexClass.getName(False),
                "signature": dexClass.getSignature(True),
                "renamed": dexClass.isRenamed()
            }
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }
        
    
    def find_method(self, class_signature, method_name):
        """Find a method by its signature in the current project"""
        try: 
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dexMethod = self._find_method(dexUnit, class_signature, method_name)
            if dexMethod is None: 
                return {"success": False, "error": "Method not found: %s" % method_name}
            
            dexResultType = "None" if dexMethod.getReturnType() is None else dexMethod.getReturnType().getSignature(True)

            return {
                "success": True, 
                "current_name": dexMethod.getName(True),
                "original_name": dexMethod.getName(False),
                "signature": dexMethod.getSignature(True),
                "result_type": dexResultType,
                "renamed": dexMethod.isRenamed(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }

    def find_field(self, class_signature, field_name):
        """Find a field by its signature in the current project"""
        try: 
            dexUnit, err = self.project_manager.get_current_dex_unit()
            if err: return err

            dexField = self._find_field(dexUnit, class_signature, field_name)
            if dexField is None: 
                return {"success": False, "error": "Field not found: %s" % field_name}
            
            return {
                "success": True, 
                "current_name": dexField.getName(True),
                "original_name": dexField.getName(False),
                "signature": dexField.getSignature(True),
                "class_type_signature": dexField.getClassTypeSignature(True),
                "renamed": dexField.isRenamed(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }
    
    def get_live_artifact_ids(self):
        """获取当前活动项目的所有活动 Artifact IDs"""
        try:
            return {"success": True, "artifact_ids": self.project_manager.get_live_artifact_ids()}
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }
    
    def switch_active_artifact(self, artifact_id):
        """切换活动 Artifact"""
        try: 
            if self.project_manager.switch_active_artifact(artifact_id):
                return {"success": True}
            return {"success": False, "error": "Failed to switch active artifact"}
        except Exception as e:
            return {
                "success": False,
                "error": (
                    "An unexpected error occurred: {exc}.\n"
                    "You may try updating JEB or this plugin to the latest version to fix potential API changes."
                ).format(exc=str(e)),
                "traceback": traceback.format_exc()
            }


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
