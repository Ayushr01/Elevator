from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import RequestElevatorAPIView

router = SimpleRouter()

urlpatterns = [
    path('request-elevator/', RequestElevatorAPIView.as_view(), name='request_elevator')
]
