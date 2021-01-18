# -*- coding: utf-8 -*-
import os
import zipfile
import logging
import subprocess

from django.conf import settings
from django.http import HttpResponse

from www.utils.crypt import make_uuid
from console.exception.main import ServiceHandleException

logger = logging.getLogger('default')


class PlatformDataServices(object):
    def get_or_create_path(self):
        data_path = settings.BASE_DIR + "/data"
        if not os.path.exists(data_path):
            os.makedirs(data_path, 0o777)
        return data_path

    def export_platform_data(self, data_path, data_type="origin"):
        console_name = self.export_console_data(data_path)
        adaptor_name = self.export_adaptor_data()
        return self.compressed_file(data_path, console_name, adaptor_name, data_type)

    def upload_file(self, data_path, upload_file, suffix):
        try:
            file_name = '{0}/{1}.{2}'.format(data_path, "import_data_{}".format(make_uuid()[:6]), suffix)
            with open(file_name, 'wb+') as destination:
                for chunk in upload_file.chunks():
                    destination.write(chunk)
                return file_name
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(msg="upload data file failed", msg_show="导入数据文件失败")

    def recover_platform_data(self, file_path):
        files = os.listdir(file_path)
        for file in files:
            if "console_data" in file:
                self.recover_console_data(file_path, file)
            if "adaptor_data" in file:
                self.recover_adaptor_data(file_path, file)

    def recover_console_data(self, file_path, file_name):
        load_command = "python3 manage.py loaddata {}".format(file_path + "/{}".format(file_name))
        load_resp = subprocess.run(load_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if load_resp.returncode != 0:
            logger.error(msg=load_resp.stderr)
            raise ServiceHandleException(msg="recover data failed", msg_show="恢复控制台数据失败")

    def recover_adaptor_data(self, file_path, file_name):
        dump_command = "{}/cloud-adaptor data import --fileName {}".format(settings.BASE_DIR,
                                                                           file_path.split('/')[-1] + "/{}".format(file_name))
        dump_resp = subprocess.run(dump_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if dump_resp.returncode != 0:
            logger.error(msg=dump_resp.stderr)
            raise ServiceHandleException(msg="export adaptor data failed", msg_show="恢复adaptor数据失败")

    def export_console_data(self, data_path):
        console_data_name = "console_data_{}.json".format(make_uuid()[:6])
        dump_command = "python3 manage.py dumpdata > {}".format(data_path + "/{}".format(console_data_name))
        dump_resp = subprocess.run(dump_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if dump_resp.returncode != 0:
            logger.error(msg=dump_resp.stderr)
            raise ServiceHandleException(msg="export console data failed", msg_show="导出控制台数据失败")
        return console_data_name

    def export_adaptor_data(self):
        adaptor_data_name = "adaptor_data_{}.json".format(make_uuid()[:6])
        dump_command = "{}/cloud-adaptor data export --fileName {}".format(settings.BASE_DIR, adaptor_data_name)
        dump_resp = subprocess.run(dump_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if dump_resp.returncode != 0:
            logger.error(msg=dump_resp.stderr)
            raise ServiceHandleException(msg="export adaptor data failed", msg_show="导出adaptor数据失败")
        return adaptor_data_name

    def compressed_file(self, data_path, console_file, adaptor_file, data_type="origin"):
        file_path = data_path + "/platform_data_{}_{}.zip".format(data_type, make_uuid()[:6])
        zip = zipfile.ZipFile(file_path, "w")
        zip.write(data_path + "/" + console_file, arcname=console_file)
        zip.write(data_path + "/" + adaptor_file, arcname=adaptor_file)
        zip.close()

        # delete source file
        os.remove(data_path + "/" + console_file)
        os.remove(data_path + "/" + adaptor_file)
        return file_path

    def upzip_file(self, file_path):
        file_name = file_path.split('/')[-1]
        extract_dir = settings.BASE_DIR + "/data/" + file_name.split('.')[0]
        os.makedirs(extract_dir, 0o777)

        file = zipfile.ZipFile(file_path, "r")
        file.extractall(extract_dir)
        return extract_dir

    def download_file(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="application/octet-stream")
                response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
                return response
        raise ServiceHandleException(msg="The file does not exist", msg_show="该文件不存在", status_code=404)


platform_data_services = PlatformDataServices()
