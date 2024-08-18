"""
WSGI config for staff_transport project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Set the default settings module for the 'django' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "staff_transport.settings")

# Get the WSGI application for use by the web server to forward requests to Django.
application = get_wsgi_application()
