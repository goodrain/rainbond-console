# -*- coding: utf8 -*-

from rest_framework import serializers


class CreateComponentGraphReq(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=True, help_text="the title of the graph")
    promql = serializers.CharField(max_length=2047, required=True, help_text="the promql of the graph")


class UpdateComponentGraphReq(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=True, help_text="the title of the graph")
    promql = serializers.CharField(max_length=2047, required=True, help_text="the promql of the graph")
    sequence = serializers.IntegerField(required=True, help_text="the sequence number of the graph")


class ExchangeComponentGraphsReq(serializers.Serializer):
    graph_ids = serializers.ListField(required=True, help_text="the graph_ids to be exchanged")
