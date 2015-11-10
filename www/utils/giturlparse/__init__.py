# Imports
from parser import parse as _parse
from result import GitUrlParsed


def parse(url, check_domain=True):
    return GitUrlParsed(_parse(url, check_domain))

def validate(url, check_domain=True):
    return parse(url, check_domain).valid
