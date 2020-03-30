# -*- coding: utf-8 -*-
from console.models.main import Applicants


class ApplyRepo(object):
    def get_applicants(self, team_name):
        return Applicants.objects.filter(team_name=team_name)

    def get_applicants_team(self, user_id):
        return Applicants.objects.filter(user_id=user_id)

    def get_append_applicants_team(self, user_id):
        return Applicants.objects.filter(user_id=user_id, is_pass=0)

    def get_applicants_by_id_team_name(self, user_id, team_name):
        return Applicants.objects.filter(user_id=user_id, team_name=team_name)

    def create_apply_info(self, **params):
        return Applicants.objects.create(**params)

    def delete_applicants_record(self, user_id, team_name, is_pass):
        Applicants.objects.filter(user_id=user_id, team_name=team_name, is_pass=is_pass).delete()


apply_repo = ApplyRepo()
