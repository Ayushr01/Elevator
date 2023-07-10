from rest_framework import serializers
from .models import System

class CreateElevatorSystemSerializer(serializers.ModelSerializer):
    """
    Serializes data for newly created elevator system
    """

    class Meta:
        model = System
        fields = '__all__'