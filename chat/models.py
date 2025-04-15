from django.db import models
from account.models import User

class ChatMessage(models.Model):
    CHAT_TYPES = (
        ('admin', 'Admin Chat'),
        ('regular', 'Regular Chat'),
    )
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    chat_type = models.CharField(max_length=10, choices=CHAT_TYPES, default='regular')

    class Meta:
        indexes = [
            models.Index(fields=['sender', 'timestamp']),
            models.Index(fields=['receiver', 'timestamp']),
            models.Index(fields=['chat_type', 'timestamp']),
            models.Index(fields=['sender', 'receiver', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.sender.username} to {self.receiver.username} ({self.chat_type})"