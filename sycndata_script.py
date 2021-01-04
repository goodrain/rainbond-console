# -*- coding: utf8 -*-
"""
  Created on 18/3/8.
"""
try:
    print("start exec file [console/syncservice/plugin_delete_script.py]")
    exec(compile(open("console/syncservice/plugin_delete_script.py", "rb").read(), "console/syncservice/plugin_delete_script.py", 'exec'))
except Exception as e:
    print(e)
