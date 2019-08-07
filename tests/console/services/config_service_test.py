# -*- coding: utf-8 -*-


def test_image_to_base64():
    from console.services.config_service import config_service
    base64 = config_service.image_to_base64("/data/media/joyce-romero-1300643-unsplash.jpg")
    print len(base64)
    # print base64
    assert 0
