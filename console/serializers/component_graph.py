# -*- coding: utf8 -*-

from rest_framework import serializers


class CreateComponentGraphReq(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=True, help_text="the title of the graph")
    promql = serializers.CharField(max_length=2047, required=True, help_text="the promql of the graph")


class UpdateComponentGraphReq(serializers.Serializer):
    graph_id = serializers.CharField(max_length=32, required=True, help_text="the identity of the graph")
    title = serializers.CharField(max_length=255, required=True, help_text="the title of the graph")
    promql = serializers.CharField(max_length=2047, required=True, help_text="the promql of the graph")
