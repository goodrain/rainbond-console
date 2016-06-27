import md5

def md5fun (digest):
    m2 = hashlib.md5()   
    m2.update(digest)   
    return m2.hexdigest()