from console.models.main import OperationLog


class OperationLogRepo(object):
    def create(self, **data):
        return OperationLog.objects.create(**data)

    def list(self):
        return OperationLog.objects.all().values()


operation_log_repo = OperationLogRepo()
