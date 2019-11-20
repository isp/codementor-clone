import json

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, response, status, views
from rest_framework.permissions import IsAuthenticated

from jobs.models import Job
from .serializers import JobPaymentSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


class PublishKeyView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return response.Response({'publicKey': settings.STRIPE_PUBLIC_KEY})


class JobPaymentDetailView(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobPaymentSerializer
    permission_classes = [IsAuthenticated]


class CreatePaymentIntentView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        job = Job.objects.get(id=request.data['job'])
        payment_intent = stripe.PaymentIntent.create(
            amount=job.budget * 100,  # this value is in cents
            currency="USD",
            payment_method_types=request.data['payment_method_types']  # e.g card, apple pay etc.
        )
        try:
            return response.Response(payment_intent)
        except Exception as e:
            return response.Response(json.dumps(str(e)), status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def webhook_receiver(request):
    # TODO
    # You can use webhooks to receive information about asynchronous payment events.
    # For more about our webhook events check out https://stripe.com/docs/webhooks.
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret)
            data = event['data']
        except Exception as e:
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']
    data_object = data['object']

    print('event ' + event_type)

    if event_type == 'payment_intent.succeeded':
        # Fulfill any orders, e-mail receipts, etc
        print("💰 Payment received!")

    if event_type == 'payment_intent.payment_failed':
        # Notify the customer that their order was not fulfilled
        print("❌ Payment failed.")

    return response.Response({'status': 'success'})
