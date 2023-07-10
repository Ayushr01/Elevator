from rest_framework import serializers
from .models import Request

class RequestSerializer(serializers.ModelSerializer):
    """
    serializes data for creating elevator request
    """
    class Meta:
        model = Request
        fields = '__all__'