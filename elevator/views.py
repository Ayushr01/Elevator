from rest_framework.generics import CreateAPIView, UpdateAPIView, ListAPIView, RetrieveAPIView
from elevator.serializers import DoorStatusSerializer, ElevatorNextFloorSerializer, MoveElevatorSerializer, RequestSerializer
from rest_framework.response import Response
from .models import DOOR_STATUS_CHOICES, ELEVATOR_STATUS_CHOICES, REQUEST_STATUS_CHOICES, Elevator, Request
from rest_framework.exceptions import ValidationError,  MethodNotAllowed
from django.db.models import F, Q

from elevator.utils import get_all_requests_for_elevator, get_floors_above_below_to_board_and_deboard, get_most_suitable_elevator, get_next_floor, get_next_floor_for_elevator, remove_people_from_undermaintainance_elevator

class RequestElevatorAPIView(CreateAPIView):
    """
    Api to request an elevator for service by a user
    This api will assign an optimal Elevator to this request according to the business logic.
    """
    serializer_class = RequestSerializer

    def perform_create(self, serializer):
        """ 
        creates a new user request and assign an optimal elevator
        """
        pickup_floor =  serializer.validated_data['pick_up_floor']
        elevator_assigned_id = get_most_suitable_elevator(pickup_floor)
        elevator_assigned_obj = Elevator.objects.filter(id=elevator_assigned_id).annotate(
            systems_max_floor = F('system__max_floors')
        ).first()
        if elevator_assigned_obj.elevator_status == ELEVATOR_STATUS_CHOICES.IDLE:
            elevator_assigned_obj.elevator_status= (
                ELEVATOR_STATUS_CHOICES.GOING_UP if (
                    pickup_floor >= elevator_assigned_obj.current_floor and
                    pickup_floor < elevator_assigned_obj.systems_max_floor
                )
                else ELEVATOR_STATUS_CHOICES.GOING_DOWN
            )
            elevator_assigned_obj.next_floor = pickup_floor
            elevator_assigned_obj.save()
        
        serializer.validated_data['elevator'] = elevator_assigned_obj
        serializer.save()

        return Response(serializer.data)


class MoveElevatorAPIview(UpdateAPIView):
    """
    APi to move elevator to next floors
    """
    queryset = Elevator.objects.all()
    serializer_class = MoveElevatorSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'elevator_id'

    def initial(self, request, *args, **kwargs):
        """
        Only patch method is allowed
        """
        super().initial(request, *args, **kwargs)
        if self.request.method != 'PATCH':
            raise MethodNotAllowed(request.method)

    def perform_update(self, serializer):
        """
        Updates the Elevators data for next_floor, current_floor, doors_status, and elevator status
        """
        instance = serializer.instance 
        if instance.door_status == DOOR_STATUS_CHOICES.OPEN:
            raise ValidationError('Cannot move the elevator please close the door first')  
        if instance.is_under_maintainance:
            raise ValidationError('Cannot move elevator as it is undermaintainance')
        # all requests for current elevator
        all_requests = get_all_requests_for_elevator(elevator_id=instance.id)
        # These request will be picked up at current floor
        #  Please Note these people have to enter their destination else exception will be raised (code logic)
        requests_with_no_destinations = all_requests.filter(
            pick_up_floor=instance.current_floor,
            destination_floor__isnull=True
        )
        if requests_with_no_destinations:
            raise ValidationError('Some users have not choosen their destination floor please choose.')
    
        #  current floor of the elevator will be next floor after moving (assumed reflects instantly)
        # instance.current_floor = instance.next_floor
        elevator_status = instance.elevator_status
        all_requests_pending = all_requests.filter(status__in=[REQUEST_STATUS_CHOICES.ACTIVE, REQUEST_STATUS_CHOICES.BOARDED])
        # If no request is pending for elevator mark status idle
        if not all_requests_pending:
            instance.next_floor = None
            instance.elevator_status = ELEVATOR_STATUS_CHOICES.IDLE
            instance.save()
            raise ValidationError('There are no request for this elevator')
        else:
            # Getting the nearest floor to reach in case where elevator is already going up / Down  or Is Idle 
            nearest_floor_above_to_board, nearest_floor_above_to_deboard, nearest_floor_down_to_board, nearest_floor_down_to_deboard = (
                get_floors_above_below_to_board_and_deboard(all_requests_pending, instance.current_floor)
            )

            if not (nearest_floor_above_to_board or nearest_floor_above_to_deboard or nearest_floor_down_to_board or nearest_floor_down_to_deboard):
                instance.current_floor = instance.next_floor
                instance.next_floor = None
                instance.elevator_status = ELEVATOR_STATUS_CHOICES.IDLE 
            else:
                instance.next_floor = get_next_floor(nearest_floor_above_to_board, nearest_floor_above_to_deboard, nearest_floor_down_to_board, nearest_floor_down_to_deboard, elevator_status, instance.current_floor)
            
            #  Marking elevator for up or down direction
            instance.elevator_status = (
                ELEVATOR_STATUS_CHOICES.GOING_UP if instance.next_floor > instance.current_floor
                else ELEVATOR_STATUS_CHOICES.GOING_DOWN
            )
            instance.current_floor = instance.next_floor
            all_requests_boarded = all_requests.filter(pick_up_floor=instance.current_floor)
            all_requests_boarded.update(status=REQUEST_STATUS_CHOICES.BOARDED)
            all_requests_fulfilled = all_requests.filter(destination_floor=instance.current_floor)
            all_requests_fulfilled.update(status=REQUEST_STATUS_CHOICES.FULFILLED)
            next_floor = get_next_floor_for_elevator(
                all_requests, elevator_status, instance.current_floor
            )
            instance.next_floor = None if next_floor == instance.current_floor else next_floor
            instance.save()


class GetActiveRequestsForElevator(ListAPIView):
    """
    View to return all active request for an elevator
    """
    serializer_class = RequestSerializer
    lookup_url_kwarg = 'elevator_id'
    
    def get_queryset(self):
        """
        returns queryset of all active requests for an elevator
        """
        elevator_id = self.kwargs.get(self.lookup_url_kwarg)
        return get_all_requests_for_elevator(elevator_id=elevator_id)


class MarkUnderMaintainanceElevator(UpdateAPIView):
    """
    View to mark elevator under maintainance and deboard all members at current floor
    also marl all active requests for this elevator as fulfilled and user can request fro new elevator
    """
    queryset = Elevator.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'elevator_id'
    serializer_class = MoveElevatorSerializer

    def initial(self, request, *args, **kwargs):
        """
        Only patch method is allowed
        """
        super().initial(request, *args, **kwargs)
        if self.request.method != 'PATCH':
            raise MethodNotAllowed(request.method)

    def perform_update(self, serializer):
        instance = serializer.instance
        instance.is_under_maintainance = True
        instance.current_floor = 0
        instance.next_floor = None
        instance.elevator_status = ELEVATOR_STATUS_CHOICES.IDLE
        instance.door_status = DOOR_STATUS_CHOICES.CLOSED
        instance.save()

        remove_people_from_undermaintainance_elevator(instance.id)
    

class OpenCloseElevatorDoors(UpdateAPIView):
    """
    Opens/closes the doors of an elevator
    """
    queryset = Elevator.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'elevator_id'
    serializer_class = DoorStatusSerializer

    def initial(self, request, *args, **kwargs):
        """
        Only patch method is allowed
        """
        super().initial(request, *args, **kwargs)
        if self.request.method != 'PATCH':
            raise MethodNotAllowed(request.method)

    def perform_update(self, serializer):
        instance = serializer.instance
        instance.door_status = DOOR_STATUS_CHOICES.OPEN if instance.door_status == DOOR_STATUS_CHOICES.CLOSED else DOOR_STATUS_CHOICES.CLOSED
        instance.save()


class GetNextFloorForElevator(RetrieveAPIView):
    """
    return the next floor the lift would be going to.
    """
    queryset = Elevator.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'elevator_id'

    def get(self, request, *args, **kwargs):
        """
        overwriting get function to retrieve latest data for next floor
        """
        all_requests = get_all_requests_for_elevator(elevator_id=self.kwargs[self.lookup_url_kwarg])
        instance = self.get_object()
        next_floor = get_next_floor_for_elevator(
            all_requests, instance.elevator_status, instance.current_floor
        )
        data = {
            "next_floor": 'Elevator has no requests either it is idle or under maintainance' if not next_floor else next_floor
        }

        return Response(data=data)


class UserDestinationFloorAPI(UpdateAPIView):
    """
    request to add destination floor to respective elevator request
    this will only happen if elevator is already alooted and elevator is at sama floor
    """
    queryset = Request.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'request_id'
    serializer_class = RequestSerializer

    def initial(self, request, *args, **kwargs):
        """
        Only patch method is allowed
        """
        super().initial(request, *args, **kwargs)
        if self.request.method != 'PATCH':
            raise MethodNotAllowed(request.method)

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.status == REQUEST_STATUS_CHOICES.FULFILLED:
            raise ValidationError('This request is already processed')
        if instance.elevator.current_floor != instance.pick_up_floor:
            raise ValidationError('Your elevator has not arrived yet please wait.')
        if instance.pick_up_floor == instance.destination_floor:
            raise ValidationError('current floor and destination floor cant be same')
        
        serializer.save()
        

