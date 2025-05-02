from rest_framework import viewsets, permissions
from products.models import Category
from products.serializers import CategorySerializer
from rest_framework.response import Response
from django.core.cache import cache
from account.permissions import IsVendor  # import your own permission

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsVendor()]

    def list(self, request, *args, **kwargs):
        cache_key = "category_list"
        categories = cache.get(cache_key)
        if not categories:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            categories = serializer.data
            cache.set(cache_key, categories, 60 * 60)
        return Response(categories)
