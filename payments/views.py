from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import response
from rest_framework import status
import stripe

from jobs.models import Job
from .models import Payment
from .serializers import StripePaymentSerializer
from .services import stripe_service

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentCreateView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated, )
    serializer_class = StripePaymentSerializer
    queryset = Payment.objects.all()

    def post(self, request, *args, **kwargs):
        # doesn't work on test visa card with the number 4242 4242 4242 4242
        token = self.request.data.get('token')
        # https://stripe.com/docs/testing#cards
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():

            """
            For now I think the amount we charge should come off of the budget of the job. 
            Instead of allowing a user to specify an amount in the API request, we can rather
            make the budget adjustable on the UI
            """
            try:
                job = Job.objects.get(id=serializer.data.get('job'))  # Validate the job belongs to the user
            except Job.DoesNotExist:
                return response.Response({"detail": "Job does not exist"}, status=status.HTTP_400_BAD_REQUEST)
            return stripe_service.charge(request.user, job.amount)

