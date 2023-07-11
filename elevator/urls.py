from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import RequestElevatorAPIView, MoveElevatorAPIview, GetActiveRequestsForElevator

router = SimpleRouter()

urlpatterns = [
    path('request-elevator', RequestElevatorAPIView.as_view(), name='request_elevator'),
    path('move-elevator/<int:pk>', MoveElevatorAPIview.as_view(), name='move-elevator'),
    path('<int:id>/get-active-requests',GetActiveRequestsForElevator.as_view(), name='elevators-requests')
]
