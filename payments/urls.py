from django.urls import path

from . import views


urlpatterns = [
    path('create/', views.PaymentCreateView.as_view())
]


