# -*- coding: utf-8 -*-
import sys


def test_image_to_base64():
    from console.services.config_service import config_service
    base64 = config_service.image_to_base64("/data/media/bg.jpg")
    print(len(base64))
    print(sys.getsizeof(base64))
    assert 0
