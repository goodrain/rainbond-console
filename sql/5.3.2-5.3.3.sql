ALTER TABLE app_service_extend_method ADD COLUMN `container_cpu` int DEFAULT 0;
ALTER TABLE tenant_service_volume ADD COLUMN `mode` int;
