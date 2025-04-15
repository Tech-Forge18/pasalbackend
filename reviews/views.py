# reviews/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Review
from .serializers import ReviewSerializer, ReviewReplySerializer
from account.permissions import IsCustomer, IsApprovedVendor
from utils.mail import send_mailersend_email  # Import the Celery task

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
            message = (
                f"Dear {vendor.username},\n\n"
                f"A customer ({self.request.user.username}) has reviewed your product '{review.product.name}'.\n"
                f"Rating: {review.rating}/5\n"
                f"Comment: {review.comment}\n\n"
                f"Check it out in your vendor dashboard.\n\n"
                f"Best regards,\nGurkha Pasal Team"
            )
            send_mailersend_email.delay(vendor.email, subject, message)

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
            message = (
                f"Dear {customer.username},\n\n"
                f"The vendor ({request.user.username}) has replied to your review on '{review.product.name}'.\n"
                f"Your Rating: {review.rating}/5\n"
                f"Your Comment: {review.comment}\n"
                f"Vendor Reply: {reply.comment}\n\n"
                f"Thank you for shopping with us!\n\n"
                f"Best regards,\nGurkha Pasal Team"
            )
            send_mailersend_email.delay(customer.email, subject, message)

        return Response(serializer.data, status=status.HTTP_201_CREATED)