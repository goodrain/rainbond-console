# -*- coding: utf8 -*-
import hashlib
import logging
import random
import re
import uuid
from io import BytesIO

from console.views.base import AlowAnyApiView
from django.conf import settings
from django.http import HttpResponse
from PIL import Image, ImageDraw, ImageFont

from_top = 4
logger = logging.getLogger('default')
current_path = settings.BASE_DIR

NON_DIGITS_RX = re.compile('[^\d]')


class CaptchaView(AlowAnyApiView):
    def getsize(self, font, text):
        if hasattr(font, 'getoffset'):
            return [x + y for x, y in zip(font.getsize(text), font.getoffset(text))]
        else:
            return font.getsize(text)

    def get(self, request, *args, **kwargs):
        """
        获取验证码
        ---
        """
        uid = str(uuid.uuid4())
        mp_src = hashlib.md5(uid.encode("UTF-8")).hexdigest()
        text = mp_src[0:4]
        request.session["captcha_code"] = text
        request.session.save()
        font_path = current_path + "/www/static/www/fonts/Vera.ttf"
        logger.debug("======> font path " + str(font_path))
        font = ImageFont.truetype(font_path, 22)

        size = self.getsize(font, text)
        size = (size[0] * 2, int(size[1] * 1.4))

        image = Image.new('RGBA', size)

        try:
            PIL_VERSION = int(NON_DIGITS_RX.sub('', Image.VERSION))
        except Exception:
            PIL_VERSION = 116
        xpos = 2

        charlist = []
        for char in text:
            charlist.append(char)

        for char in charlist:
            fgimage = Image.new('RGB', size, '#001100')
            charimage = Image.new('L', self.getsize(font, ' %s ' % char), '#000000')
            chardraw = ImageDraw.Draw(charimage)
            chardraw.text((0, 0), ' %s ' % char, font=font, fill='#ffffff')
            if PIL_VERSION >= 116:
                charimage = charimage.rotate(random.randrange(*(-35, 35)), expand=0, resample=Image.BICUBIC)
            else:
                charimage = charimage.rotate(random.randrange(*(-35, 35)), resample=Image.BICUBIC)
            charimage = charimage.crop(charimage.getbbox())
            maskimage = Image.new('L', size)

            maskimage.paste(charimage, (xpos, from_top, xpos + charimage.size[0], from_top + charimage.size[1]))
            size = maskimage.size
            image = Image.composite(fgimage, image, maskimage)
            xpos = xpos + 2 + charimage.size[0]

        image = image.crop((0, 0, xpos + 1, size[1]))

        ImageDraw.Draw(image)

        out = BytesIO()
        image.save(out, "PNG")
        out.seek(0)

        response = HttpResponse(content_type='image/png')
        response.write(out.read())
        response['Content-length'] = out.tell()

        return response
