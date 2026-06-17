"""
WSGI config for goodrain_web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

# Static files are served by whitenoise.middleware.WhiteNoiseMiddleware
# (the old whitenoise.django.DjangoWhiteNoise wrapper was removed in whitenoise 4).
application = get_wsgi_application()
