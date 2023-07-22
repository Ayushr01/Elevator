from django.urls import include, path
from rest_framework.routers import SimpleRouter
from .views import (
    ElevatorViewSet, RequestViewSet
)

router = SimpleRouter()
router.register('', ElevatorViewSet)
request_router = SimpleRouter()
request_router.register('', RequestViewSet)



urlpatterns = [
    # Include the custom actions as separate URL patterns.
    path('<int:elevator_id>/move-elevator', ElevatorViewSet.as_view({'patch': 'move_elevator'}), name='move-elevator'),
    path('<int:elevator_id>/get-active-requests', ElevatorViewSet.as_view({'get': 'get_all_active_request'}), name='get_all_active_requests'),
    path('<int:elevator_id>/open-close-doors', ElevatorViewSet.as_view({'patch': 'open_close_doors'}), name='open_close_doors'),
    path('<int:elevator_id>/under-maintainance', ElevatorViewSet.as_view({'patch': 'mark_under_maintainance'}), name='mark_under_maintainance'),
    path('<int:elevator_id>/next-floor', ElevatorViewSet.as_view({'get': 'get_next_floor'}), name='get_next_floor'),
    path('request-elevator/', include(request_router.urls)),
]
