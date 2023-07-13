from rest_framework import viewsets
from django.db import transaction
from elevator.models import Elevator
from rest_framework.response import Response
from .models import System
from rest_framework.exceptions import ValidationError

from system.serializers import CreateElevatorSystemSerializer

class CreateElevatorSystemView(viewsets.ModelViewSet):
    """
    View to create an elevator system.
    """
    queryset = System.objects.all()
    serializer_class = CreateElevatorSystemSerializer
    http_method_names = ['get', 'post']
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)
        current_system_instance = serializer.save()

        number_of_elevators = request.data['elevators_count']
        elevators_to_create = []
        for _ in range(number_of_elevators):
            obj = Elevator(system=current_system_instance)
            #  adding to list of new elevators to be created
            elevators_to_create.append(obj)
        
        #  bulk creating elevators
        Elevator.objects.bulk_create(elevators_to_create)

        return Response(serializer.data)
            
