from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from multiselectfield import MultiSelectField
from choices import LANGUAGES, TIME_ZONES, TECHNOLOGIES
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(default='profile_default.jpg', upload_to='profile_images')
    social_accounts = models.TextField(blank=True)
    time_zone = models.CharField(max_length=5, choices=TIME_ZONES, blank=True)
    languages = MultiSelectField(choices=LANGUAGES, blank=True)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'{self.user} profile'


class Freelancer(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    bio = models.TextField()
    technologies = MultiSelectField(choices=TECHNOLOGIES)
    stripe_account_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f'{self.profile.user} freelancer'


def profile_post_save_receiver(sender, instance, **kwargs):
    profile, created = Profile.objects.get_or_create(user=instance)
    if created:
        customer = stripe.Customer.create(email=instance.email)
        profile.stripe_customer_id = customer['id']
        profile.save()


post_save.connect(profile_post_save_receiver, sender=User)
