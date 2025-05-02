# products/views/category.py
from rest_framework import viewsets, permissions
from django.core.cache import cache
from rest_framework.response import Response
from products.models import Category
from products.serializers import CategorySerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        cache_key = "category_list"
        categories = cache.get(cache_key)
        if not categories:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            categories = serializer.data
            cache.set(cache_key, categories, 60 * 60)  # Cache for 1 hour
        return Response(categories)
