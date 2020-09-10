# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
from .app_relation_service import AppServiceRelationService
from .deploy_type_service import DeployTypeService
from .domain_service import DomainService
from .env_service import AppEnvService, AppEnvVarService
from .extend_service import AppExtendService
from .image_relation_service import AppImageRelationService
from .label_service import LabelService
from .mnt_service import AppMntService
from .port_service import AppPortService, EndpointService
from .probe_service import ProbeService
from .service_monitor import ComponentServiceMonitor
from .volume_service import AppVolumeService

port_service = AppPortService()
endpoint_service = EndpointService()
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
deploy_type_service = DeployTypeService()
component_service_monitor = ComponentServiceMonitor()
