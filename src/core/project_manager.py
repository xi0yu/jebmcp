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
        self.active_artifact = None
    
    def _validate_ctx(self):
        if self.ctx is None:
            raise Exception("No JEB context available")
    
    def _get_current_project(self):
        """Get the current main project from JEB context"""
        self._validate_ctx()
        return self.ctx.getMainProject()

    def get_live_artifacts(self):
        """Get a list of live artifacts from JEB context"""
        prj = self._get_current_project()
        if prj is None:
            raise Exception("No JEB project available")
        
        return prj.getLiveArtifacts()

    def get_current_artifact(self):
        """Get the current artifact from JEB context"""
        if self.active_artifact is not None:
            return self.active_artifact, None
            
        artifacts = self.get_live_artifacts()
        if not artifacts or len(artifacts) == 0:
            return None, {"success": False, "error": "No JEB artifacts available"}
        
        auto_selected = [x for x in artifacts if x.getMainUnit().getFormatType() == "apk"]
        if not auto_selected or len(auto_selected) == 0:
            return None, {"success": False, "error": "No APK artifact available"}
        
        self.active_artifact = auto_selected[0]
        return self.active_artifact, None
    
    def get_current_apk_unit(self):
        """Get the current DEX unit from JEB context"""
        artifact, err = self.get_current_artifact()
        if err: return None, err

        if artifact is None:
            return None, {"success": False, "error": "No JEB artifact available" }
        mainUnit = artifact.getMainUnit()
        if mainUnit is None:
            return None, {"success": False, "error": "No main unit available in artifact" }
        if mainUnit.getFormatType() == "apk":
            apk_unit = mainUnit.getDex()
            if apk_unit is None:
                return None, {"success": False, "error": "No DEX unit found in APK" }
            return apk_unit, None
        return None, {"success": False, "error": "Current artifact is not an APK unit" }
    def get_current_dex_unit(self):
        """Get the current DEX unit from JEB context"""
        apkUnit, err = self.get_current_apk_unit()
        if err is not None:
            return None, err
        if apkUnit is None:
            return None, {"success": False, "error": "No APK unit available" }
        return apkUnit, None

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
    
    def get_project_details(self):
        apk_units = [
            x.getMainUnit()
            for x in self.get_live_artifacts()
            if x.getMainUnit().getFormatType() == "apk"
        ]
        if not apk_units:
            return {
                "success": False,
                "error": "No APK unit found in the project"
            }

        results = []

        for apk_unit in apk_units:
            package_name = apk_unit.getPackageName() or "Unknown"
            application_class_name = apk_unit.getApplicationName() or "Unknown"

            activity_count = len(apk_unit.getActivities() or [])
            service_count = len(apk_unit.getServices() or [])
            receiver_count = len(apk_unit.getReceivers() or [])
            provider_count = len(apk_unit.getProviders() or [])

            permissions = apk_unit.getPermissions()
            permissions = list(permissions) if permissions else []

            results.append({
                "package_name": package_name,
                "application_class": application_class_name,
                "permissions": permissions,
                "activities": activity_count,
                "services": service_count,
                "receivers": receiver_count,
                "providers": provider_count,
            })


        return {
            "count": len(results),
            "apk_list": results
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
            live_artifact_length = len([ x for x in self.get_live_artifacts() if x.getMainUnit().getFormatType() == "apk"])
            has_projects = live_artifact_length > 0
            
            return {
                "success": True, 
                "has_projects": has_projects,
                "project_count": live_artifact_length
            }
        except Exception as e:
            return {"success": False, "error": "Failed to check projects: %s" % str(e)}
    
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

    def get_live_artifact_ids(self):
        """Get a list of live artifact IDs"""
        return [
            x.getMainUnit().getName()
            for x in self.get_live_artifacts()
            if x.getMainUnit().getFormatType() == "apk"
        ] or []

    def switch_active_artifact(self, artifact_id):
        """Switch the active artifact in JEB"""
        prj = self._get_current_project()
        if prj is None:
            return False
        
        selected_artifact = [x for x in prj.getLiveArtifacts() if x.getMainUnit().getName() == artifact_id]
        if not selected_artifact:
            return False
        
        self.active_artifact = selected_artifact[0]
        return True
