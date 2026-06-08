"""
ASGI config for truck_Cargo project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from apps.trucks import *


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'truck_Cargo.settings')

ws_patterns = [
    path('test/', testconsumer.as_asgi()),  # ← also add .as_asgi()
]

application = ProtocolTypeRouter({
    'http': get_asgi_application(),   # ← HTTP handler must be here
    'websocket': URLRouter(ws_patterns),
})
