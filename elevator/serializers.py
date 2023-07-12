from rest_framework import serializers
from .models import Request, Elevator
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

    def validate_is_under_maintainance(self, value):
        """
        checks if the elevator to move is under maintainance the raise exception
        """
        if value:
            raise ValidationError('Cannot move elevator as it is undermaintainance')
        
        return value

    def validate_door_status(self, value):
        """
        If door is open raise validation for closing it
        """
        if value == 'Open':
            raise ValidationError('Cannot move the elevator please close the door first')

        return value


class DoorStatusSerializer(MoveElevatorSerializer):
    """
    returns door status of elevator
    """
    class Meta(MoveElevatorSerializer.Meta):
        fields = ('door_status',)