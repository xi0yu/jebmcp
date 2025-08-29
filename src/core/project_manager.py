# -*- coding: utf-8 -*-
"""
Project manager module - handles JEB project and unit management
"""
from com.pnfsoftware.jeb.core.units.code.android import IApkUnit, IDexUnit

class ProjectManager(object):
    """Manages JEB project and unit operations"""
    
    def __init__(self, ctx):
        self.ctx = ctx
    
    def get_current_project(self):
        """Get the current main project from JEB context"""
        if self.ctx is None:
            return None
        return self.ctx.getMainProject()
    
    def find_apk_unit(self, project):
        """Find APK unit in the given project"""
        if project is None:
            return None
        return project.findUnit(IApkUnit)
    
    def find_dex_unit(self, project):
        """Find DEX unit in the given project"""
        if project is None:
            return None
        return project.findUnit(IDexUnit)
    
    def is_project_loaded(self):
        """Check if a project is currently loaded"""
        project = self.get_current_project()
        return project is not None
    
    def get_project_info(self):
        """Get basic information about the current project"""
        project = self.get_current_project()
        if project is None:
            return None
        
        info = {
            'has_apk_unit': self.find_apk_unit(project) is not None,
            'has_dex_unit': self.find_dex_unit(project) is not None
        }
        return info
