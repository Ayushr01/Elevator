from django.db import models
from system.models import System

class Elevator(models.Model):
    """
    Elevator model
    """
    door_status_choices = (
        ('Open', 'Open'),
        ('closed', 'closed')
    )
    elevator_status_choices = (
        ('Going_up', 'Going_up'),
        ('Going_down', 'Going_down'),
        ('Idle', 'Idle')
    )

    system = models.ForeignKey(System, on_delete=models.CASCADE)
    current_floor = models.PositiveIntegerField(default=0)
    next_floor = models.PositiveIntegerField(null=True)
    is_under_maintainance = models.BooleanField(default=False)
    door_status = models.CharField(choices=door_status_choices, default='Closed')
    elevator_status = models.CharField(choices=elevator_status_choices, default='Idle')


class Request(models.Model):
    """
    Model for a Request
    """
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Fulfilled', 'Fulfilled')
    )
    pick_up_floor = models.BigIntegerField()
    destination_floor = models.BigIntegerField(null=True)
    elevator = models.ForeignKey(Elevator, on_delete=models.CASCADE, null=True) 
    status = models.CharField(choices=STATUS_CHOICES, default='Active')

