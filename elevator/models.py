from collections import namedtuple
from django.db import models
from system.models import System

RequestStatusChoices = namedtuple('RequestStatusChoices', ['ACTIVE', 'BOARDED', 'FULFILLED'])
DoorStatusChoices = namedtuple('DoorStatusChoices', ['OPEN', 'CLOSED'])
ElevatorStatusChoices = namedtuple('ElevatorStatusChoices', ['GOING_UP', 'GOING_DOWN', 'IDLE'])

DOOR_STATUS_CHOICES = DoorStatusChoices(OPEN='Open', CLOSED='Closed')
ELEVATOR_STATUS_CHOICES = ElevatorStatusChoices(GOING_UP='Going_up', GOING_DOWN='Going_down', IDLE='Idle')
REQUEST_STATUS_CHOICES = RequestStatusChoices(ACTIVE='Active', BOARDED='Boarded', FULFILLED='Fulfilled')


class Elevator(models.Model):
    """
    Elevator model
    """

    door_status_choices = [
        (getattr(DOOR_STATUS_CHOICES, attr), attr.capitalize()) for attr in DOOR_STATUS_CHOICES._fields
    ]
    elevator_status_choices = [
        (getattr(ELEVATOR_STATUS_CHOICES, attr), attr.capitalize()) for attr in ELEVATOR_STATUS_CHOICES._fields
    ]

    system = models.ForeignKey(System, on_delete=models.CASCADE)
    current_floor = models.PositiveIntegerField(default=0)
    next_floor = models.PositiveIntegerField(null=True)
    is_under_maintainance = models.BooleanField(default=False)
    door_status = models.CharField(choices=door_status_choices, default=DOOR_STATUS_CHOICES.CLOSED)
    elevator_status = models.CharField(choices=elevator_status_choices, default=ELEVATOR_STATUS_CHOICES.IDLE)


class Request(models.Model):
    """
    Model for a Request
    """
    STATUS_CHOICES = [
        (getattr(REQUEST_STATUS_CHOICES, attr), attr.capitalize()) for attr in REQUEST_STATUS_CHOICES._fields
    ]
    pick_up_floor = models.BigIntegerField()
    destination_floor = models.BigIntegerField(null=True)
    elevator = models.ForeignKey(Elevator, on_delete=models.CASCADE, null=True) 
    status = models.CharField(choices=STATUS_CHOICES, default=REQUEST_STATUS_CHOICES.ACTIVE)

