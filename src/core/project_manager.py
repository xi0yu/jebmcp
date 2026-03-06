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
        """Get the current artifact from JEB context (supports APK and DEX formats)"""
        if self.active_artifact is not None:
            return self.active_artifact, None

        artifacts = self.get_live_artifacts()
        if not artifacts or len(artifacts) == 0:
            return None, {"success": False, "error": "No JEB artifacts available"}

        # 支持 APK 和 DEX 两种格式
        auto_selected = [x for x in artifacts if x.getMainUnit().getFormatType() in ("apk", "dex")]
        if not auto_selected or len(auto_selected) == 0:
            return None, {"success": False, "error": "No APK or DEX artifact available"}

        self.active_artifact = auto_selected[0]
        return self.active_artifact, None
    
    def get_current_apk_unit(self):
        """Get the current APK unit from JEB context (returns None for DEX-only artifacts)"""
        artifact, err = self.get_current_artifact()
        if err: return None, err

        if artifact is None:
            return None, {"success": False, "error": "No JEB artifact available"}
        mainUnit = artifact.getMainUnit()
        if mainUnit is None:
            return None, {"success": False, "error": "No main unit available in artifact"}
        if mainUnit.getFormatType() == "apk":
            return mainUnit, None
        # DEX 格式返回 None（不是错误，只是没有 APK unit）
        return None, None

    def get_current_dex_unit(self):
        """Get the current DEX unit from JEB context (supports both APK and standalone DEX)"""
        artifact, err = self.get_current_artifact()
        if err: return None, err

        if artifact is None:
            return None, {"success": False, "error": "No JEB artifact available"}

        mainUnit = artifact.getMainUnit()
        if mainUnit is None:
            return None, {"success": False, "error": "No main unit available in artifact"}

        format_type = mainUnit.getFormatType()
        if format_type == "apk":
            # APK 格式：从 APK unit 获取 DEX
            return mainUnit.getDex(), None
        elif format_type == "dex":
            # DEX 格式：mainUnit 就是 IDexUnit
            return mainUnit, None

        return None, {"success": False, "error": "Unsupported artifact format: %s" % format_type}

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
        # 支持 APK 和 DEX 格式
        units = [
            x.getMainUnit()
            for x in self.get_live_artifacts()
            if x.getMainUnit().getFormatType() in ("apk", "dex")
        ]
        if not units:
            return {
                "success": False,
                "error": "No APK or DEX unit found in the project"
            }

        results = []
        for unit in units:
            format_type = unit.getFormatType()

            if format_type == "apk":
                # APK 格式的详细信息
                package_name = unit.getPackageName() or "Unknown"
                application_class_name = unit.getApplicationName() or "Unknown"
                activity_count = len(unit.getActivities() or [])
                service_count = len(unit.getServices() or [])
                receiver_count = len(unit.getReceivers() or [])
                provider_count = len(unit.getProviders() or [])
                permissions = list(unit.getPermissions()) if unit.getPermissions() else []

                results.append({
                    "format_type": "apk",
                    "package_name": package_name,
                    "application_class": application_class_name,
                    "permissions": permissions,
                    "activities": activity_count,
                    "services": service_count,
                    "receivers": receiver_count,
                    "providers": provider_count,
                })
            else:
                # DEX 格式的详细信息
                results.append({
                    "format_type": "dex",
                    "name": unit.getName() or "Unknown",
                })

        return {
            "count": len(results),
            "artifact_list": results
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
            # 支持 APK 和 DEX 格式
            live_artifact_length = len([
                x for x in self.get_live_artifacts()
                if x.getMainUnit().getFormatType() in ("apk", "dex")
            ])
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
        """Get a list of live artifact IDs (supports APK and DEX formats)"""
        return [
            x.getMainUnit().getName()
            for x in self.get_live_artifacts()
            if x.getMainUnit().getFormatType() in ("apk", "dex")
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
