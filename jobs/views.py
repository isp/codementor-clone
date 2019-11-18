from django.core.exceptions import PermissionDenied
from django.conf import settings
from rest_framework import generics
from rest_framework import views
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
import stripe

from .models import Job
from .serializers import JobSerializer
from .permissions import IsOwnerOrReadOnly


stripe.api_key = settings.STRIPE_SECRET_KEY


class JobListCreateView(generics.ListCreateAPIView):
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Job.objects.filter(taken=False).order_by('-timestamp')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class JobDetailEditDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def put(self, request, *args, **kwargs):
        data = request.data
        job = Job.objects.get(pk=kwargs['pk'])

        job.summary = data.get('summary', job.summary)
        job.details = data.get('details', job.details)
        job.technologies = data.get('technologies', job.technologies)
        job.deadline = data.get('deadline', job.deadline)
        job.budget = data.get('budget', job.budget)
        job.save()

        return Response(JobSerializer(job, context=self.get_serializer_context()).data, status.HTTP_200_OK)


class ApplyForJobView(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if hasattr(user.profile, 'freelancer'):
            job = Job.objects.get(pk=self.kwargs['pk'])

            if user in job.applicants.all():
                job.applicants.remove(user)
            else:
                job.applicants.add(user)
            return self.retrieve(request, *args, **kwargs)
        raise PermissionDenied


class PaymentView(views.APIView):
    def post(self, request, *args, **kwargs):
        order = get_object_or_404(Order, user=self.request.user, ordered=False)
        user_profile = get_object_or_404(UserProfile, user=self.request.user)
        # doesn't work on test visa card with the number 4242 4242 4242 4242
        token = self.request.data.get('stripeToken')
        # https://stripe.com/docs/testing#cards
        # token = 'tok_visa'
        billing_address_id = self.request.data.get('selectedBillingAddress')
        shipping_address_id = self.request.data.get('selectedShippingAddress')
        billing_address = Address.objects.get(id=billing_address_id)
        shipping_address = Address.objects.get(id=shipping_address_id)

        if user_profile.stripe_customer_id != '' and user_profile.stripe_customer_id is not None:
            customer = stripe.Customer.retrieve(
                user_profile.stripe_customer_id)
            customer.sources.create(source=token)

        else:
            customer = stripe.Customer.create(
                email=self.request.user.email,
            )
            customer.sources.create(source=token)
            user_profile.stripe_customer_id = customer['id']
            user_profile.one_click_purchasing = True
            user_profile.save()

        amount = int(order.get_total() * 100)

        try:
            # create a charge (https://stripe.com/docs/api/charges/create?lang=python)
            # charge the customer because we cannot charge the token more than once
            charge = stripe.Charge.create(
                amount=amount,  # cents
                currency="usd",
                customer=user_profile.stripe_customer_id)

            # charge once off on the token
            # charge = stripe.Charge.create(
            #     amount=amount,  # cents
            #     currency="usd",
            #     source=token  # obtained with Stripe.js
            # )

            # create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            # assign the payment to the order

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered = True
            order.payment = payment
            order.billing_address = billing_address
            order.shipping_address = shipping_address
            # order.ref_code = generate_ref_code()
            order.save()

            return Response({'message': 'Your order was successful!'}, status=status.HTTP_200_OK)

        # stripe error handling (https://stripe.com/docs/api/errors/handling?lang=python)
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error', {})
            return Response({'message': f"{err.get('message')}"}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            return Response(
                {'message': 'Too many requests made to the API too quickly'},
                status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            return Response(
                {'message': "Invalid parameters were supplied to Stripe's API"},
                status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            return Response(
                {'message': "Authentication with Stripe's API failed"},
                status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            return Response(
                {'message': 'Network communication with Stripe failed'},
                status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            return Response(
                {'message': 'Something went wrong. You were not charged. Please try again'},
                status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # send an email to myself because there's something wrong with my code
            return Response(
                {'message': 'Serious error occurred. We have been notified'},
                status=status.HTTP_400_BAD_REQUEST)
