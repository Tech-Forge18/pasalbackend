from rest_framework import serializers
from .models import ChatMessage
from account.models import User

class AdminChatSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)
    receiver = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='admin'))
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'receiver', 'receiver_username', 'message', 'timestamp', 'is_read', 'chat_type']
        read_only_fields = ['sender', 'timestamp', 'is_read', 'chat_type']

    def validate(self, data):
        user = self.context['request'].user
        receiver = data.get('receiver')

        if user.role != 'vendor':
            raise serializers.ValidationError("Only vendors can send admin chat messages.")
        if receiver.role != 'admin':
            raise serializers.ValidationError("Admin chat must be sent to an admin.")

        return data

class RegularChatSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)
    receiver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'receiver', 'receiver_username', 'message', 'timestamp', 'is_read', 'chat_type']
        read_only_fields = ['sender', 'timestamp', 'is_read', 'chat_type']

    def validate(self, data):
        user = self.context['request'].user
        receiver = data.get('receiver')

        if user.role == 'customer' and receiver.role != 'vendor':
            raise serializers.ValidationError("Customers can only chat with vendors.")
        elif user.role == 'vendor' and receiver.role != 'customer':
            raise serializers.ValidationError("Vendors can only chat with customers in regular chat.")
        elif user.role == 'admin':
            raise serializers.ValidationError("Admins cannot use regular chat.")

        return data