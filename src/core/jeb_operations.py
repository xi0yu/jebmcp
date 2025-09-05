# -*- coding: utf-8 -*-
"""
JEB operations module - handles all business logic for APK/DEX operations
"""
import hashlib
from com.pnfsoftware.jeb.core.units.code.android import IApkUnit, IDexUnit
from com.pnfsoftware.jeb.core.util import DecompilerHelper
from com.pnfsoftware.jeb.core.output.text import TextDocumentUtil
from com.pnfsoftware.jeb.core.actions import ActionXrefsData, Actions, ActionContext, ActionOverridesData

# Import signature utilities using absolute path for JEB compatibility
import sys
import os

# Add the src directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from utils.signature_utils import convert_class_signature
except ImportError:
    # Fallback: define the function inline if import fails
    import re
    def convert_class_signature(class_name):
        """Fallback implementation of convert_class_signature"""
        if not class_name:
            return None
        pattern = r'^L[^;]+;$'
        if re.match(pattern, class_name):
            return class_name
        else:
            return 'L' + class_name.replace('.', '/') + ';'

class JebOperations(object):
    """Handles all JEB-specific operations for APK/DEX analysis"""
    
    def __init__(self, project_manager, ctx=None):
        self.project_manager = project_manager
        self.ctx = ctx
    
    def get_manifest(self):
        """Get the manifest of the currently loaded APK project in JEB"""
        project = self.project_manager.get_current_project()
        if project is None:
            print('No project currently loaded in JEB')
            return None
        
        # Find APK unit via project
        apk_unit = self.project_manager.find_apk_unit(project)
        if apk_unit is None:
            print('No APK unit found in the current project')
            return None
        
        man = apk_unit.getManifest()
        if man is None:
            print('No manifest found in the APK unit')
            return None
        
        doc = man.getFormatter().getPresentation(0).getDocument()
        text = TextDocumentUtil.getText(doc)
        return text
    
    def get_method_decompiled_code(self, method_signature):
        """Get the decompiled code of the given method in the currently loaded APK project"""
        if not method_signature:
            return None

        project = self.project_manager.get_current_project()
        if project is None:
            print('No project currently loaded in JEB')
            return None
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            print('No dex unit found in the current project')
            return None
        
        method = dex_unit.getMethod(method_signature)
        if method is None:
            print('Method not found: %s' % method_signature)
            return None
        
        decomp = DecompilerHelper.getDecompiler(dex_unit)
        if not decomp:
            print('Cannot acquire decompiler for unit: %s' % decomp)
            return None

        if not decomp.decompileMethod(method.getSignature()):
            print('Failed decompiling method')
            return None

        text = decomp.getDecompiledMethodText(method.getSignature())
        return text
    
    def get_class_decompiled_code(self, class_signature):
        """Get the decompiled code of a class in the current APK project"""
        if not class_signature:
            return None

        project = self.project_manager.get_current_project()
        if project is None:
            print('No project currently loaded in JEB')
            return None

        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            print('No dex unit found in the current project')
            return None
        
        # normalize class signature for JNI format before lookup
        normalized_signature = convert_class_signature(class_signature)
        clazz = dex_unit.getClass(normalized_signature)
        if clazz is None:
            print('Class not found: %s' % normalized_signature)
            return None
        
        decomp = DecompilerHelper.getDecompiler(dex_unit)
        if not decomp:
            print('Cannot acquire decompiler for unit: %s' % decomp)
            return None

        if not decomp.decompileClass(clazz.getSignature()):
            print('Failed decompiling class')
            return None

        text = decomp.getDecompiledClassText(clazz.getSignature())
        return text
    
    def get_method_callers(self, method_signature):
        """Get the callers of the given method in the currently loaded APK project"""
        if not method_signature:
            return None

        project = self.project_manager.get_current_project()
        if project is None:
            print('No project currently loaded in JEB')
            return None
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            print('No dex unit found in the current project')
            return None
        
        ret = []
        method = dex_unit.getMethod(method_signature)
        if method is None:
            print("Method not found: %s" % method_signature)
            return None
        
        action_xrefs_data = ActionXrefsData()
        action_context = ActionContext(dex_unit, Actions.QUERY_XREFS, method.getItemId(), None)
        if dex_unit.prepareExecution(action_context, action_xrefs_data):
            for i in range(action_xrefs_data.getAddresses().size()):
                ret.append((action_xrefs_data.getAddresses()[i], action_xrefs_data.getDetails()[i]))
        return ret
    
    def get_field_callers(self, field_signature):
        """Get the callers/references of the given field in the currently loaded APK project"""
        if not field_signature:
            return None

        project = self.project_manager.get_current_project()
        if project is None:
            print('No project currently loaded in JEB')
            return None
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            print('No dex unit found in the current project')
            return None
        
        ret = []
        # Parse field signature to get class and field name
        # Field signature format: Lcom/example/Class;->fieldName:Type
        if '->' not in field_signature:
            print("Invalid field signature format. Expected: Lcom/example/Class;->fieldName:Type")
            return None
        
        class_part, field_part = field_signature.split('->', 1)
        if not class_part.endswith(';'):
            class_part += ';'
        
        # Get the class first
        clazz = dex_unit.getClass(class_part)
        if clazz is None:
            print("Class not found: %s" % class_part)
            return None
        
        # Find the field in the class
        field = None
        for f in clazz.getFields():
            if f.getSignature() == field_signature:
                field = f
                break
        
        if field is None:
            print("Field not found: %s" % field_signature)
            return None
        
        # Use the same approach as method callers - query cross-references
        action_xrefs_data = ActionXrefsData()
        action_context = ActionContext(dex_unit, Actions.QUERY_XREFS, field.getItemId(), None)
        if dex_unit.prepareExecution(action_context, action_xrefs_data):
            for i in range(action_xrefs_data.getAddresses().size()):
                ret.append((action_xrefs_data.getAddresses()[i], action_xrefs_data.getDetails()[i]))
        return ret
    
    def get_method_overrides(self, method_signature):
        """Get the overrides of the given method in the currently loaded APK project"""
        if not method_signature:
            return None

        project = self.project_manager.get_current_project()
        if project is None:
            print('No project currently loaded in JEB')
            return None
        
        dex_unit = self.project_manager.find_dex_unit(project)
        if dex_unit is None:
            print('No dex unit found in the current project')
            return None
        
        ret = []
        method = dex_unit.getMethod(method_signature)
        if method is None:
            print("Method not found: %s" % method_signature)
            return None
        
        data = ActionOverridesData()
        action_context = ActionContext(dex_unit, Actions.QUERY_OVERRIDES, method.getItemId(), None)
        if dex_unit.prepareExecution(action_context, data):
            for i in range(data.getAddresses().size()):
                ret.append((data.getAddresses()[i], data.getDetails()[i]))
        return ret
    
    def set_class_name(self, class_name, new_name):
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
    
    def set_method_name(self, class_name, method_name, new_name):
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
            return {"success": False, "error": "Failed to rename method '%s' in class %s: %s" % (method_name, normalized_signature, str(e))}
    
    def set_field_name(self, class_name, field_name, new_name):
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
            return {"success": False, "error": "Failed to rename field '%s' in class %s: %s" % (field_name, normalized_signature, str(e))}
    
    def get_smali_instructions(self, class_signature, method_name):
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
                        "signature": method.getSignature(),
                        "name": method.getName(),
                        "descriptor": method.getDescriptor(),
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
            instruction_count = method.getInstructions().getInstructionCount()
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
    
    def check_status(self):
        """Get detailed status information about JEB and loaded projects"""
        try:
            # Check MCP to JEB connection
            connection_status = "connected"
            try:
                # Try a simple ping to verify connection
                project = self.project_manager.get_current_project()
                if project is None:
                    connection_status = "disconnected"
            except Exception:
                connection_status = "disconnected"
            
            # Get project info
            projects_info = []
            if connection_status == "connected":
                try:
                    project_info = self._get_project_details(project)
                    if project_info:
                        projects_info.append(project_info)
                except Exception as e:
                    print("Error getting project: %s" % str(e))
            
            # Get JEB version info (optional)
            jeb_version = self.ctx.getSoftwareVersion().toString()
            
            return {
                "connection": {
                    "status": connection_status,
                    "message": "MCP to JEB connection status"
                },
                "projects": {
                    "count": len(projects_info),
                    "details": projects_info
                },
                "jeb_version": jeb_version
            }
            
        except Exception as e:
            return {
                "connection": {
                    "status": "error",
                    "message": "Failed to check status: %s" % str(e)
                },
                "projects": {
                    "count": 0,
                    "details": []
                },
                "jeb_version": None
            }
    
    def _get_project_details(self, project):
        try:
            dex_class_count = 0
            dex_method_count = 0
            dex_field_count = 0

            for dex_unit in project.findUnits(IDexUnit):
                dex_class_count += len(dex_unit.getClasses())
                dex_method_count += len(dex_unit.getMethods())
                dex_field_count += len(dex_unit.getFields())

            package_name = "Unknown"
            application_entry_class_name = "Unknown"
            manifest_component_count = [
                ("activities", 0),
                ("services", 0),
                ("receivers", 0),
                ("providers", 0)
            ]

            for apk_unit in project.findUnits(IApkUnit):
                if not apk_unit.hasApplication():
                    continue
                package_name = apk_unit.getPackageName() or "Unknown"
                application_entry_class_name = apk_unit.getApplicationName() or "Unknown"
                manifest_component_count = [
                    ("activities", len(apk_unit.getActivities())),
                    ("services", len(apk_unit.getServices())),
                    ("receivers", len(apk_unit.getReceivers())),
                    ("providers", len(apk_unit.getProviders()))
                ]
                break

            return {
                "package_name": package_name,
                "application_entry_class_name": application_entry_class_name,
                "dex_class_count": dex_class_count,
                "dex_method_count": dex_method_count,
                "dex_field_count": dex_field_count,
                "manifest_component_count": manifest_component_count
            }

        except Exception as e:
            print("Error getting project details: %s" % str(e))
            return {
                "package_name": "Error",
                "application_entry_class_name": "Error",
                "dex_class_count": 0,
                "dex_method_count": 0,
                "dex_field_count": 0,
                "manifest_component_count": []
            }

    