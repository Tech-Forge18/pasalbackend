# reviews/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Review
from .serializers import ReviewSerializer, ReviewReplySerializer
from account.permissions import IsCustomer, IsApprovedVendor
from utils.mail import send_mailersend_email
import logging

logger = logging.getLogger('gurkha_pasal')

class CustomerReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for customers to create and view their own reviews."""
    serializer_class = ReviewSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        review = serializer.save(user=self.request.user)
        # Send email to vendor asynchronously
        vendor = review.product.vendor
        if vendor.email:
            subject = f"New Review on Your Product: {review.product.name}"
            message = f"""
Dear {vendor.username},

You have received a new review on your product "{review.product.name}" (Code: {review.product.code}).

Rating: {review.rating}/5
Comment: {review.comment or 'No comment provided'}

You can view and respond to the review in your vendor dashboard.

Best regards,
Gurkha Pasal Team
"""
            try:
                send_mailersend_email.delay(vendor.email, subject, message)
            except Exception as e:
                logger.error(f"Failed to send review email to vendor {vendor.username}: {str(e)}")

class VendorReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for vendors to view and reply to reviews on their products."""
    serializer_class = ReviewSerializer
    permission_classes = [IsApprovedVendor]

    def get_queryset(self):
        # Show reviews for products owned by the vendor
        return Review.objects.filter(product__vendor=self.request.user)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Vendor replies to a review on their product (one reply per review)."""
        review = self.get_object()
        if review.product.vendor != request.user:
            return Response(
                {"detail": "You can only reply to reviews on your products"},
                status=status.HTTP_403_FORBIDDEN
            )
        # Check if vendor has already replied
        if review.replies.filter(user=request.user).exists():
            return Response(
                {"detail": "You can only reply once per review"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = ReviewReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = serializer.save(user=request.user, review=review)

        # Send email to customer asynchronously
        customer = review.user
        if customer.email:
            subject = f"Vendor Reply to Your Review on {review.product.name}"
            message = f"""
Dear {customer.username},

The vendor ({request.user.username}) has replied to your review on "{review.product.name}" (Code: {review.product.code}).

Your Rating: {review.rating}/5
Your Comment: {review.comment or 'No comment provided'}
Vendor Reply: {reply.comment}

Thank you for shopping with us!

Best regards,
Gurkha Pasal Team
"""
            try:
                send_mailersend_email.delay(customer.email, subject, message)
            except Exception as e:
                logger.error(f"Failed to send reply email to customer {customer.username}: {str(e)}")

        return Response(serializer.data, status=status.HTTP_201_CREATED)