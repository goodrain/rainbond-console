# -*- coding: utf-8 -*-


def test_image_to_base64():
    from console.services.config_service import config_service
    base64 = config_service.image_to_base64("/data/media/21940d2566e94ef3a2d7569f09b25ba1.png")
    print base64
    assert 0
