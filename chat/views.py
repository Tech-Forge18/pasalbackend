from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.dateparse import parse_datetime
from django.db import models
from .models import ChatMessage
from .serializers import AdminChatSerializer, RegularChatSerializer
from account.permissions import IsVendor, IsCustomer, IsAdmin
from rest_framework.pagination import PageNumberPagination

class ChatMessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminChatViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor-to-admin chat."""
    serializer_class = AdminChatSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor | IsAdmin]
    pagination_class = ChatMessagePagination

    def get_queryset(self):
        return ChatMessage.objects.filter(
            models.Q(sender=self.request.user) | models.Q(receiver=self.request.user),
            chat_type='admin'
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, chat_type='admin')

    def get_queryset_filters(self):
        queryset = self.get_queryset()
        receiver_id = self.request.query_params.get('receiver', None)
        if receiver_id:
            queryset = queryset.filter(receiver__id=receiver_id)
        after = self.request.query_params.get('after', None)
        if after:
            after_time = parse_datetime(after)
            if after_time:
                queryset = queryset.filter(timestamp__gt=after_time)
        return queryset

    def get_queryset(self):
        return self.get_queryset_filters()

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        if message.receiver != request.user:
            return Response(
                {"detail": "You can only mark messages as read if you are the receiver."},
                status=status.HTTP_403_FORBIDDEN
            )
        message.is_read = True
        message.save()
        return Response({"detail": "Message marked as read."}, status=status.HTTP_200_OK)

class RegularChatViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor-to-customer chat."""
    serializer_class = RegularChatSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor | IsCustomer]
    pagination_class = ChatMessagePagination

    def get_queryset(self):
        return ChatMessage.objects.filter(
            models.Q(sender=self.request.user) | models.Q(receiver=self.request.user),
            chat_type='regular'
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, chat_type='regular')

    def get_queryset_filters(self):
        queryset = self.get_queryset()
        receiver_id = self.request.query_params.get('receiver', None)
        if receiver_id:
            queryset = queryset.filter(receiver__id=receiver_id)
        after = self.request.query_params.get('after', None)
        if after:
            after_time = parse_datetime(after)
            if after_time:
                queryset = queryset.filter(timestamp__gt=after_time)
        return queryset

    def get_queryset(self):
        return self.get_queryset_filters()

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        if message.receiver != request.user:
            return Response(
                {"detail": "You can only mark messages as read if you are the receiver."},
                status=status.HTTP_403_FORBIDDEN
            )
        message.is_read = True
        message.save()
        return Response({"detail": "Message marked as read."}, status=status.HTTP_200_OK)