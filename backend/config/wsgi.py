"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()


# On Vercel the disk is read-only except /tmp, and every new server instance starts empty.
# The data is tiny (about 120 rows), so each instance builds its own database from the
# CSV files when it starts.
if os.environ.get("VERCEL"):
    import io

    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=0)
    call_command("import_data", stdout=io.StringIO())
