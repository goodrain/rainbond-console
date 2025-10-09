# -*- coding: utf-8 -*-
import logging
import os
import shutil
import subprocess
import time
import zipfile

import requests
from console.exception.main import ServiceHandleException
from django.conf import settings
from django.http import HttpResponse
from www.utils.crypt import make_uuid

logger = logging.getLogger('default')


class PlatformDataBackupServices(object):
    def list_backups(self):
        g = os.walk(settings.DATA_DIR + "/backups/")
        if not os.path.exists(os.path.join(settings.DATA_DIR, "backups")):
            os.makedirs(os.path.join(settings.DATA_DIR, "backups"), 0o777)
        backups = []
        for path, _, file_list in g:
            file_list.sort()
            file_list.reverse()
            for file in file_list:
                if file.endswith(".tar.gz"):
                    size = os.path.getsize(os.path.join(path, file))
                    backups.append({"name": file, "size": size})
        return backups

    def remove_backup(self, name):
        os.remove(settings.DATA_DIR + "/backups/" + name)

    def create_backup(self):
        backup_path = settings.DATA_DIR + "/backups/" + time.strftime("%Y-%m-%d", time.localtime())
        if not os.path.exists(backup_path):
            os.makedirs(backup_path, 0o777)
        self.export_console_data(backup_path)
        self.write_version(backup_path)
        tarname = "rainbond-console-backup-data-{0}.tar.gz".format(time.strftime("%Y%m%d%H%M%S", time.localtime()))
        full_tarname = os.path.join(settings.DATA_DIR, "backups", tarname)
        self.compressed_file_by_tar(backup_path, full_tarname)
        shutil.rmtree(backup_path)

    def write_version(self, backup_path):
        with open(os.path.join(backup_path, 'version'), 'w') as f:
            f.write(settings.VERSION)

    def version_than(self, backup_path):
        with open(os.path.join(backup_path, 'version'), 'w') as f:
            if f.read() != settings.VERSION:
                raise ServiceHandleException(
                    msg="The data version is inconsistent with the code version.", msg_show="数据版本不同，不能导入")

    def upload_file(self, upload_file):
        try:
            if not os.path.exists(os.path.join(settings.DATA_DIR, "backups")):
                os.makedirs(os.path.join(settings.DATA_DIR, "backups"), 0o777)
            file_name = os.path.join(settings.DATA_DIR, "backups", upload_file.name)
            with open(file_name, 'wb+') as destination:
                for chunk in upload_file.chunks():
                    destination.write(chunk)
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(msg="upload data file failed", msg_show="导入数据文件失败")

    def recover_platform_data(self, name):
        recover_path = os.path.join(settings.DATA_DIR, "backups", "recover-{}".format(make_uuid()[:6]))
        if not os.path.exists(recover_path):
            os.makedirs(recover_path, 0o777)
        self.un_compressed_file_by_tar(recover_path, name)
        files = os.listdir(recover_path)
        for file in files:
            if "console_data" in file:
                self.recover_console_data(os.path.join(recover_path, file))
        shutil.rmtree(recover_path)

    def recover_console_data(self, file_name):
        # 首先尝试使用自定义的 restore_backup 命令（如果存在）
        # 该命令会处理重复键的问题
        try:
            # 检查自定义命令是否存在
            check_command = "python3 manage.py help restore_backup"
            check_resp = subprocess.run(check_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")

            if check_resp.returncode == 0:
                # 使用自定义命令，它会处理重复键
                load_command = "python3 manage.py restore_backup {} --update-on-conflict".format(file_name)
                logger.info("Using custom restore_backup command to handle duplicates")
            else:
                # 退回到标准的 loaddata 命令，但使用更智能的恢复策略
                logger.info("Custom restore_backup command not found, using smart recovery")
                self._smart_recover_console_data(file_name)
                return

            load_resp = subprocess.run(load_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")

            if load_resp.returncode != 0:
                # 如果自定义命令失败，尝试智能恢复
                logger.warning("Custom restore command failed, trying smart recovery: {}".format(load_resp.stderr))
                self._smart_recover_console_data(file_name)
        except Exception as e:
            logger.error("Error during data recovery: {}".format(e))
            # 如果所有方法都失败，尝试智能恢复作为最后手段
            self._smart_recover_console_data(file_name)

    def _smart_recover_console_data(self, file_name):
        """智能恢复控制台数据，处理重复键问题"""
        import json
        from django.apps import apps
        from django.db import transaction, connection

        logger.info("Starting smart recovery for console data")

        try:
            # 读取备份数据
            with open(file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 按模型分组数据
            objects_by_model = {}
            for obj in data:
                model_label = obj.get('model')
                if model_label:
                    if model_label not in objects_by_model:
                        objects_by_model[model_label] = []
                    objects_by_model[model_label].append(obj)

            # 处理每个模型
            for model_label, objects in objects_by_model.items():
                app_label, model_name = model_label.split('.')

                try:
                    model = apps.get_model(app_label, model_name)
                except LookupError:
                    logger.warning("Model {} not found, skipping...".format(model_label))
                    continue

                logger.info("Processing {}: {} records".format(model_label, len(objects)))

                # 特殊处理 ConsoleSysConfig
                if model_name == 'ConsoleSysConfig':
                    self._restore_console_sys_config(model, objects)
                else:
                    self._restore_generic_model(model, objects)

            logger.info("Smart recovery completed successfully")

        except Exception as e:
            logger.error("Smart recovery failed: {}".format(e))
            raise ServiceHandleException(msg="recover data failed", msg_show="恢复控制台数据失败")

    def _restore_console_sys_config(self, model, objects):
        """特殊处理 ConsoleSysConfig 的恢复"""
        success_count = 0
        update_count = 0

        for obj_data in objects:
            fields = obj_data.get('fields', {})
            pk = obj_data.get('pk')

            try:
                with transaction.atomic():
                    # 检查记录是否存在（基于唯一键）
                    key_value = fields.get('key')
                    if key_value:
                        existing = model.objects.filter(key=key_value).first()

                        if existing:
                            # 更新现有记录
                            for field_name, field_value in fields.items():
                                if field_name != 'key':  # 不更新键字段
                                    setattr(existing, field_name, field_value)
                            existing.save()
                            update_count += 1
                            logger.debug("Updated ConsoleSysConfig: {}".format(key_value))
                        else:
                            # 创建新记录
                            obj = model(**fields)
                            if pk:
                                obj.pk = pk
                            obj.save()
                            success_count += 1
                            logger.debug("Created ConsoleSysConfig: {}".format(key_value))
            except Exception as e:
                logger.error("Error processing ConsoleSysConfig {}: {}".format(fields.get('key', 'unknown'), e))
                continue

        logger.info("ConsoleSysConfig: {} created, {} updated".format(success_count, update_count))

    def _restore_generic_model(self, model, objects):
        """通用模型恢复"""
        success_count = 0
        error_count = 0

        # 获取唯一字段
        unique_fields = []
        for field in model._meta.get_fields():
            if getattr(field, 'unique', False) and not field.primary_key:
                unique_fields.append(field.name)

        for obj_data in objects:
            fields = obj_data.get('fields', {})
            pk = obj_data.get('pk')

            try:
                with transaction.atomic():
                    # 如果有唯一字段，检查是否存在
                    if unique_fields:
                        lookup = {}
                        for field in unique_fields:
                            if field in fields:
                                lookup[field] = fields[field]

                        if lookup:
                            existing = model.objects.filter(**lookup).first()
                            if existing:
                                # 更新现有记录
                                for field_name, field_value in fields.items():
                                    setattr(existing, field_name, field_value)
                                existing.save()
                                success_count += 1
                                continue

                    # 创建新记录
                    obj = model(**fields)
                    if pk:
                        obj.pk = pk
                    obj.save()
                    success_count += 1

            except Exception as e:
                error_count += 1
                logger.debug("Error restoring {}: {}".format(model.__name__, e))
                continue

        if success_count > 0:
            logger.info("{}: {} records restored successfully".format(model.__name__, success_count))
        if error_count > 0:
            logger.warning("{}: {} records failed".format(model.__name__, error_count))

    def recover_adaptor_data(self, file_name):
        files = {'file': open(file_name, 'rb')}
        remoteurl = "http://{0}:{1}/{2}".format(
            os.getenv("ADAPTOR_HOST", "127.0.0.1"), os.getenv("ADAPTOR_PORT", "8080"), "enterprise-server/api/v1/recover")
        r = requests.post(remoteurl, files=files)
        if r.status_code != 200:
            raise ServiceHandleException(msg="export adaptor data failed", msg_show="恢复adaptor数据失败")

    def export_console_data(self, data_path):
        console_data_name = "console_data.json"
        dump_command = "python3 manage.py dumpdata --exclude auth.permission --exclude contenttypes > {}".format(
            data_path + "/{}".format(console_data_name))
        dump_resp = subprocess.run(dump_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if dump_resp.returncode != 0:
            logger.error(msg=dump_resp.stderr)
            raise ServiceHandleException(msg="export console data failed", msg_show="导出控制台数据失败")
        return console_data_name

    def compressed_file_by_tar(self, backup_path, tarname):

        dump_resp = subprocess.run(
            "tar -czf {0} ./".format(tarname),
            shell=True,
            cwd=backup_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8")
        if dump_resp.returncode != 0:
            logger.error(msg=dump_resp.stderr)
            raise ServiceHandleException(msg="export adaptor data failed", msg_show="备份数据打包失败")

    def un_compressed_file_by_tar(self, recover_path, tarname):
        dump_resp = subprocess.run(
            "tar -xzf {0} -C {1}".format(tarname, recover_path),
            shell=True,
            cwd=settings.DATA_DIR + "/backups/",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8")
        if dump_resp.returncode != 0:
            logger.error(msg=dump_resp.stderr)
            raise ServiceHandleException(msg="export adaptor data failed", msg_show="备份数据解压失败")

    def upzip_file(self, file_path):
        file_name = file_path.split('/')[-1]
        extract_dir = settings.BASE_DIR + "/data/" + file_name.split('.')[0]
        os.makedirs(extract_dir, 0o777)

        file = zipfile.ZipFile(file_path, "r")
        file.extractall(extract_dir)
        return extract_dir

    def download_file(self, file_name):
        file_path = os.path.join(settings.DATA_DIR, "backups", file_name)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="application/octet-stream")
                response['Content-Disposition'] = 'inline; filename=' + file_name
                return response
        raise ServiceHandleException(msg="The file does not exist", msg_show="该备份文件不存在", status_code=404)


platform_data_services = PlatformDataBackupServices()
