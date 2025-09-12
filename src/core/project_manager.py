# -*- coding: utf-8 -*-
"""
Project manager module - handles JEB project and unit management
"""
import os
import re
from com.pnfsoftware.jeb.core.units.code.android import IApkUnit, IDexUnit
from com.pnfsoftware.jeb.core import ILiveArtifact, JebCoreService, ICoreContext, Artifact, RuntimeProjectUtil
from com.pnfsoftware.jeb.core.input import FileInput
from java.io import File
from java.lang import Throwable

class ProjectManager(object):
    """Manages JEB project and unit operations"""
    
    def __init__(self, ctx):
        self.ctx = ctx
    
    def _validate_ctx(self):
        if self.ctx is None:
            raise Exception("No JEB context available")
    
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
    
    def get_project_details(self, project):
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
            return {
                "package_name": "Error",
                "application_entry_class_name": "Error",
                "dex_class_count": 0,
                "dex_method_count": 0,
                "dex_field_count": 0,
                "manifest_component_count": [],
                "error_message": str(e)
            }

    def load_project(self, file_path):
        """Open a new project from file path
        
        Args:
            file_path (str): Path to the APK/DEX file to open
            
        Returns:
            dict: Success status and project information
        """
        try:
            self._validate_ctx()
            engines_context = self.ctx.getEnginesContext()
            if engines_context is None:
                return {"success": False, "error": "No JEB context available"}

            if not os.path.exists(file_path):
                return {"success": False, "error": "File not found: %s" % file_path}
            
            base_name = os.path.basename(file_path)
            project = engines_context.loadProject(base_name)
            correspondingArtifact = None
            for artifact in project.getLiveArtifacts():
                if artifact.getArtifact().getName() == base_name:
                    correspondingArtifact = artifact
                    break
            if not correspondingArtifact:
                correspondingArtifact = project.processArtifact(Artifact(base_name, FileInput(File(file_path))))
            
            
            unit = correspondingArtifact.getMainUnit()
            if isinstance(unit, IApkUnit):
                return {"success": True, "message": "Project opened successfully"}
            
            return {"success": False, "error": "Unsupported unit type for file: %s" % file_path}
            
        except Exception as e:
            return {
                "success": False, 
                "error": "Failed to open project: %s" % str(e)
            }

    def has_projects(self):
        """Check if there are any projects loaded in JEB"""
        try:
            self._validate_ctx()
            engines_context = self.ctx.getEnginesContext()
            if engines_context is None:
                return {"success": False, "error": "No engines context available"}
            
            projects = engines_context.getProjects()
            has_projects = projects is not None and len(projects) > 0
            
            return {
                "success": True, 
                "has_projects": has_projects,
                "project_count": len(projects) if projects else 0
            }
        except Exception as e:
            return {"success": False, "error": "Failed to check projects: %s" % str(e)}
    
    def get_projects(self):
        """Get information about all loaded projects in JEB"""
        try:
            self._validate_ctx()
            engines_context = self.ctx.getEnginesContext()
            if engines_context is None:
                return {"success": False, "error": "No engines context available"}
            
            projects = engines_context.getProjects()
            if projects is None or len(projects) == 0:
                return {"success": True, "projects": []}
            
            project_list = []
            for project in projects:
                project_list.append(self.get_project_details(project))
            
            return {"success": True, "projects": project_list}
        except Exception as e:
            return {"success": False, "error": "Failed to get projects: %s" % str(e)}
    
    def unload_projects(self):
        """Unload all projects from JEB"""
        try:
            self._validate_ctx()
            engines_context = self.ctx.getEnginesContext()
            if engines_context is None:
                return {"success": False, "error": "No engines context available"}
            
            unloaded_count = len(engines_context.getProjects())
            engines_context.unloadProjects()

            return {
                "success": True, 
                "message": "Unloaded %d project(s)" % unloaded_count,
                "unloaded_count": unloaded_count
            }
        except Throwable as e:
            return {"success": False, "error": "Failed to unload projects: %s" % str(e)}
