import hashlib


def md5fun(digest):
    m = hashlib.md5(bytes(digest, "ascii"))
    return m.hexdigest()


def get_md5(fname):
    tmp_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            tmp_md5.update(chunk)
    return tmp_md5.hexdigest()
