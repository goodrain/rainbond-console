# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
from console.models.main import RainbondCenterApp


class RainbondCenterAppRepository(object):
    def get_rainbond_app_by_id(self, id):
        rain_bond_apps = RainbondCenterApp.objects.filter(ID=id)
        if rain_bond_apps:
            return rain_bond_apps[0]
        return None

    def get_all_rainbond_apps(self):
        return RainbondCenterApp.objects.all()

    def get_complete_rainbond_apps(self):
        return RainbondCenterApp.objects.filter(is_complete=True)


rainbond_app_repo = RainbondCenterAppRepository()