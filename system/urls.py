from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import CreateElevatorSystemView

router = SimpleRouter()
router.register('', CreateElevatorSystemView)

urlpatterns = router.urls
