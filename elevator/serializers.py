from rest_framework import serializers
from .models import REQUEST_STATUS_CHOICES, Request, Elevator
from rest_framework.exceptions import ValidationError


class RequestSerializer(serializers.ModelSerializer):
    """
    serializes data for creating elevator request
    """
    class Meta:
        model = Request
        fields = '__all__'


class MoveElevatorSerializer(serializers.ModelSerializer):
    """
    Serializes data for Elevator
    """

    class Meta:
        model = Elevator
        fields = '__all__'


class DoorStatusSerializer(MoveElevatorSerializer):
    """
    returns door status of elevator
    """
    class Meta(MoveElevatorSerializer.Meta):
        fields = ('door_status',)


class ElevatorNextFloorSerializer(serializers.Serializer):
    """
    returns next floor of the elevator journey
    """
    next_floor = serializers.SerializerMethodField()

    def get_next_floor(self, obj):
        return 'Elevator has no requests either it is idle or under maintainance' if not obj.next_floor else obj.next_floor

    class Meta:
        fields = ('next_floor',)
    

class  AddDestianationFloorSerialzer(serializers.Serializer):
    """
    """
    destination_floor = serializers.IntegerField(required=True)

    class Meta:
        fields = ('destination_floor', )
    
    def validate_status(self, value):
        if value == REQUEST_STATUS_CHOICES.FULFILLED:
            raise ValidationError('This request is already processed')
        return value