# -*- coding: utf8 -*-
import re
import base64


class DockerfileItem(object):
    def __init__(self, line):
        self.active = True
        if line.startswith('#'):
            self.active = False

        l = line.strip(' ')
        if l.startswith('ENV'):
            k, v = l.split(' ', )
        self.line = line

    @property
    def is_env_item(self):
        

    @property
    def is_port_item(self):
        pass

    @property
    def is_volume_item(self):
        pass

class DockerFile(object):
    @classmethod
    def parse(cls, content, encoding='base64'):
        if encoding == 'base64':
            content = base64.urlsafe_b64decode(content)
        lines = map(lambda x: x.rstrip('\r'), content.split('\n'))
        return cls.analytics(lines)

    @classmethod
    def analytics(cls, lines):
        items = {
            "env": [], "port": None, "volume": None,
        }
