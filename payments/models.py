from django.contrib.auth import get_user_model
from django.db import models
from jobs.models import Job

User = get_user_model()


class Payment(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stripe_charge_id = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('job', 'user'),
        )

    def __str__(self):
        return self.user.username
