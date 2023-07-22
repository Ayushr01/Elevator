from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import ElevatorSystemViewSet

router = SimpleRouter()
router.register('', ElevatorSystemViewSet)

urlpatterns = router.urls
