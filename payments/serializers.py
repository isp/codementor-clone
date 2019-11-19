from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id', 'job', 'user', 'timestamp'
        )
        read_only_fields = (
            'id', 'timestamp'
        )


class StripePaymentSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=100)
    job = serializers.IntegerField()
