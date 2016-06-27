import md5

def md5fun (digest): 
    m1 = md5.new()   
    m1.update(digest)   
    return m1.hexdigest()
