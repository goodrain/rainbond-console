# -*- coding: utf8 -*-
from console.constants import PluginImage


def is_runner(image):
    return image.startswith('goodrain.me/runner') or image.startswith(PluginImage.RUNNER)
