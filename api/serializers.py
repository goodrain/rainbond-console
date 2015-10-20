from rest_framework import serializers
from www.region import RegionInfo


class TenantMoveSerializer(serializers.Serializer):
    source_region = serializers.CharField(required=True)
    dest_region = serializers.CharField(required=True)

    def validate(self, data):
        for k in ('source_region', 'dest_region'):
            v = data[k]
            if k not in RegionInfo.region_names():
                raise serializers.ValidationError("{0} filed value {1} is not in region_list".format(k, v))

        return data
