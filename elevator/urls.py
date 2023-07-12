from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import (
    RequestElevatorAPIView, MoveElevatorAPIview, GetActiveRequestsForElevator,
    OpenCloseElevatorDoors, GetNextFloorForElevator, MarkUnderMaintainanceElevator,
    UserDestinationFloorAPI
)

router = SimpleRouter()

urlpatterns = [
    path('request-elevator', RequestElevatorAPIView.as_view(), name='request_elevator'),
    path('<int:elevator_id>/move-elevator', MoveElevatorAPIview.as_view(), name='move-elevator'),
    path('<int:elevator_id>/get-active-requests',GetActiveRequestsForElevator.as_view(), name='elevators-requests'),
    path('<int:elevator_id>/open-close-doors',OpenCloseElevatorDoors.as_view(), name='elevators-requests'),
    path('<int:elevator_id>/next-floor',GetNextFloorForElevator.as_view(), name='elevators-next-floor'),
    path('<int:elevator_id>/under-maintainance',MarkUnderMaintainanceElevator.as_view(), name='under-maintainance-elevator'),
    path('<int:request_id>/add-destination',UserDestinationFloorAPI.as_view(), name='add-destination-floor'),


]
