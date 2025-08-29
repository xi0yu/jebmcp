# -*- coding: utf-8 -*-
"""
JEB operations module - handles all business logic for APK/DEX operations
"""
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
    
    def __init__(self, project_manager):
        self.project_manager = project_manager
    
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
