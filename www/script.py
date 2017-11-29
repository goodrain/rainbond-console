from www.models import App, AppUsing
from www.db import BaseConnection


class AppStatistic(object):

    def update_using(self, service_key):
        app = App.objects.only('ID').get(service_key=service_key)
        dsn = BaseConnection()
        sql = "select count(1) as Count, creater as user_id from tenant_service where service_key='{}' group by creater".format(service_key)
        result = dsn.query(sql)
        for i in result:
            using, created = AppUsing.objects.get_or_create(app_id=app.pk, user_id=i.user_id)
            using.install_count = i.Count
            using.save(update_fields=['install_count'])

        app.using = AppUsing.objects.filter(app_id=app.pk).count()
        app.save()
