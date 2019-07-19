# -*- coding: utf-8 -*-
# creater by: barnett

from rest_framework import serializers


class TeamInfoSerializer(serializers.Serializer):
    enterprise_id = serializers.CharField(max_length=32)
    region_name = serializers.CharField(max_length=30)
    team_name = serializers.CharField(max_length=50)
