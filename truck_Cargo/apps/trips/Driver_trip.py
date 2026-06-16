from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from urllib.parse import parse_qs
from rest_framework_simplejwt.tokens import AccessToken
from apps.models import User
from channels.db import database_sync_to_async
from rest_framework_simplejwt.exceptions import TokenError  # ← CRITICAL IMPORT


class trip(AsyncJsonWebsocketConsumer):

    async def connect(self):
        query_string = self.scope["query_string"].decode()
        params = parse_qs(query_string)
        token = params.get("token")[0]
        try:
            # 2. Validate token and fetch user
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            
            # Fetch user asynchronously
            self.user = await database_sync_to_async(User.objects.get)(id=user_id)
            
            # Setup group name based on validated user
            self.room_group_name = f"user_{self.user.id}"

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # Accept valid connection
            await self.accept()
            await self.send_json({"status": "connected"})

        except (TokenError, User.DoesNotExist) as e:
            # 3. Handle invalid token or user not found
            # We must temporarily accept the connection to transmit the WS JSON error frame
            await self.accept()
            await self.send_json({
                "status": "error",
                "message": "Access token is invalid or expired"
            })
            # Close connection cleanly with a custom close code (4000-4999 are private use)
            await self.close(code=4401)
            return

    async def receive(self, text_data=None):
        print("Received message:", text_data)
        await self.send(text_data=json.dumps("Data recieved"))

    async def disconnect(self,close_code ):
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def send_notification(self, event):
        print("Notification event received:", event)
        await self.send_json(event.get('value'))
        