# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
from .port_service import AppPortService
from .image_relation_service import AppImageRelationService
from .env_service import AppEnvVarService, AppEnvService
from .app_relation_service import AppServiceRelationService
from .volume_service import AppVolumeService
from .mnt_service import AppMntService
from .domain_service import DomainService
from .probe_service import ProbeService
from .label_service import LabelService
from .extend_service import AppExtendService

port_service = AppPortService()
image_relation_service = AppImageRelationService()
env_var_service = AppEnvVarService()
volume_service = AppVolumeService()
dependency_service = AppServiceRelationService()
mnt_service = AppMntService()
domain_service = DomainService()
probe_service = ProbeService()
label_service = LabelService()
extend_service = AppExtendService()
compile_env_service = AppEnvService()