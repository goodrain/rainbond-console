from django.db import models


class GrOptionsCharField(models.CharField):

    def __getattr__(self, name):
        options = getattr(self, 'options')
        keys = options.split(',')
        return bool(name in keys)
