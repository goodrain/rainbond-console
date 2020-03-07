# -*- coding: utf8 -*-
from console.constants import PluginImage


def is_slug(image, lang):
    return image.startswith('goodrain.me/runner') or image.startswith(PluginImage.RUNNER) \
        and lang not in ("dockerfile", "docker")
