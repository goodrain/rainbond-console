# -*- mode: python -*-

block_cipher = None
                 #('/usr/local/lib/python2.7/dist-packages/crispy_forms/templates', 'crispy_forms/templates'),


a = Analysis(['console_app.py'],
             pathex=['./'],
             binaries=[],
             datas=[('www/templates', 'www/templates'), ('www/templatetags', 'www/templatetags'),
                 ('/usr/local/lib/python2.7/dist-packages/crispy_forms/templates', 'crispy_forms/templates'),
                 ('www/static', 'www/static')],
             hiddenimports=['gunicorn.glogging', 'gunicorn.workers.sync', 'django.core.cache.backends.memcached', 'django.core.context_processors'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='console_app',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='console_app')
