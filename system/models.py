from django.db import models

class System(models.Model):
    """
    Model to store each elevator systems
    """
    name = models.CharField(max_length=60)
    elevators_count = models.IntegerField()
    max_floors = models.IntegerField()
