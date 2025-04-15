import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message
from account.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Connect user to their personal chat group."""
        self.user = self.scope['user']  # Authenticated user from AuthMiddlewareStack
        self.group_name = f"chat_{self.user.id}"  # Unique group per user
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()  # Accept WebSocket connection

    async def disconnect(self, close_code):
        """Remove user from group on disconnect."""
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming messages from client."""
        data = json.loads(text_data)
        receiver_username = data['receiver']
        content = data['content']

        # Validate receiver and save message
        receiver = await database_sync_to_async(User.objects.get)(username=receiver_username)
        if self.user.role == 'vendor' and not self.user.is_approved:
            await self.send(text_data=json.dumps({'error': 'Only approved vendors can send messages'}))
            return

        message = await database_sync_to_async(Message.objects.create)(
            sender=self.user,
            receiver=receiver,
            content=content
        )

        # Send message to receiver’s group
        await self.channel_layer.group_send(
            f"chat_{receiver.id}",
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'sender': self.user.username,
                    'receiver': receiver.username,
                    'content': content,
                    'timestamp': message.timestamp.isoformat(),
                    'is_read': False
                }
            }
        )

        # Echo back to sender
        await self.send(text_data=json.dumps({
            'message': {
                'id': message.id,
                'sender': self.user.username,
                'receiver': receiver.username,
                'content': content,
                'timestamp': message.timestamp.isoformat(),
                'is_read': False
            }
        }))

    async def chat_message(self, event):
        """Send message to client when received from group."""
        await self.send(text_data=json.dumps(event))