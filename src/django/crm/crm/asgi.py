"""
ASGI config for CRM project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from channels.routing import get_default_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # WebSocket support can be added here
    # "websocket": AuthMiddlewareStack(
    #     URLRouter(
    #         # your websocket routing here
    #     )
    # ),
})