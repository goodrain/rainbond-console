# -*- coding: utf-8 -*-
from rest_framework import serializers


class StrictBooleanField(serializers.BooleanField):
    def to_internal_value(self, data):
        if type(data) is not bool:
            raise serializers.ValidationError("Must be a valid boolean.")
        return data


class LoginSecurityConfigSerializer(serializers.Serializer):
    login_captcha_enabled = StrictBooleanField(required=True)
    login_limit_enabled = StrictBooleanField(required=True)

    def validate(self, attrs):
        unexpected = set(self.initial_data.keys()) - set(self.fields.keys())
        if unexpected:
            raise serializers.ValidationError({"unexpected_fields": sorted(unexpected)})
        return attrs
