# Imports
from .base import BasePlatform


class GrGitLabPlatform(BasePlatform):
    PATTERNS = {
        'http': r'http://(?P<domain>.+)/(?P<owner>.+)/(?P<repo>.+).git',
        'https': r'https://(?P<domain>.+)/(?P<owner>.+)/(?P<repo>.+).git',
        'ssh': r'git@(?P<domain>.+):(?P<owner>.+)/(?P<repo>.+).git',
        'git': r'git://(?P<domain>.+)/(?P<owner>.+)/(?P<repo>.+).git',
    }
    FORMATS = {
        'http': r'http://(?P<domain>.+)/(?P<owner>.+)/(?P<repo>.+).git',
        'https': r'https://%(domain)s/%(owner)s/%(repo)s.git',
        'ssh': r'git@%(domain)s:%(owner)s/%(repo)s.git',
        'git': r'git://%(domain)s/%(owner)s/%(repo)s.git'
    }
    DOMAINS = ('code.goodrain.com',)
    DEFAULTS = {
        '_user': 'git'
    }
