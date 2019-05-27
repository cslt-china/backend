"""
WSGI config for cslt project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os

from cslt import config
from django.core.wsgi import get_wsgi_application
from prometheus_client import start_http_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cslt.settings")

# Exports Prometheus metrics.
start_http_server(config.PROMETHEUS_PORT)

application = get_wsgi_application()
