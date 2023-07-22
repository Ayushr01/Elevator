from elevator.serializers import AddDestianationFloorSerialzer, DoorStatusSerializer, MoveElevatorSerializer, RequestSerializer
from rest_framework.response import Response
from .models import DOOR_STATUS_CHOICES, ELEVATOR_STATUS_CHOICES, REQUEST_STATUS_CHOICES, Elevator, Request
from rest_framework.exceptions import ValidationError,  MethodNotAllowed
from django.db.models import F, Q
from rest_framework import viewsets
from rest_framework.decorators import action

from elevator.utils import get_all_requests_for_elevator, get_floors_above_below_to_board_and_deboard, get_most_suitable_elevator, get_next_floor, get_next_floor_for_elevator, remove_people_from_undermaintainance_elevator

class ElevatorViewSet(viewsets.ModelViewSet):
    """
    Viewset for all operations on the Elevator.
    """
    queryset = Elevator.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'elevator_id'

    def get_serializer_class(self):
        """
        Return different serializers based on the action being performed.
        """
        if self.action == 'get_all_active_request':
            return RequestSerializer
        elif self.action == 'open_close_doors':
            return DoorStatusSerializer
        else:
            return MoveElevatorSerializer


    @action(detail=True, methods=['patch'])
    def move_elevator(self, request, elevator_id=None):
        """
        action to implement the logic of move elevator to next optimal floor
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_move_elevator(serializer)
        return Response(serializer.data)


    @action(detail=True, methods=['get'])
    def get_all_active_request(self, request, elevator_id=None):
        """
        get action which returns the list of all requests in active/boarded state for current elevator
        """
        instance = self.get_object()
        serializer = RequestSerializer(get_all_requests_for_elevator(elevator_id=instance.id), many=True)
        return Response(serializer.data)


    @action(detail=True, methods=['get'])
    def get_next_floor(self, request, elevator_id=None):
        """
        get action which return the next floor this elevator will be going to
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
    

    @action(detail=True, methods=['patch'])
    def mark_under_maintainance(self, request, elevator_id=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_mark_under_maintainance(serializer)
        return Response(serializer.data)

    
    @action(detail=True, methods=['patch'])
    def open_close_doors(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update_doors(serializer)
        return Response(serializer.data)


    def perform_move_elevator(self, serializer):
        """
        Updates the Elevators data for next_floor, current_floor, doors_status, and elevator status
        """
        instance = serializer.instance 
        previous_floor = instance.current_floor
        if instance.door_status == DOOR_STATUS_CHOICES.OPEN:
            raise ValidationError('Cannot move the elevator please close the door first')  
        if instance.is_under_maintainance:
            raise ValidationError('Cannot move elevator as it is undermaintainance')
        # all requests for current elevator
        all_requests = get_all_requests_for_elevator(elevator_id=instance.id)
        #  Please Note these people have to enter their destination else exception will be raised (code logic)
        requests_with_no_destinations = all_requests.filter(
            pick_up_floor=instance.current_floor,
            destination_floor__isnull=True
        ).values_list('id', flat=True)

        if requests_with_no_destinations:
            raise ValidationError(f"Some users have not choosen their destination floor please choose. thier ids are ({','.join(map(str, requests_with_no_destinations))})")
    
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
            # These request will be picked up at current floor
            all_requests_boarded = all_requests.filter(Q(pick_up_floor=instance.current_floor) | Q(pick_up_floor = previous_floor))
            all_requests_boarded.update(status=REQUEST_STATUS_CHOICES.BOARDED)
            all_requests_fulfilled = all_requests.filter(destination_floor=instance.current_floor)
            all_requests_fulfilled.update(status=REQUEST_STATUS_CHOICES.FULFILLED)
            next_floor = get_next_floor_for_elevator(
                all_requests, elevator_status, instance.current_floor
            )
            instance.next_floor = None if next_floor == instance.current_floor else next_floor
            instance.save()
        

    def perform_mark_under_maintainance(self, serializer):
        """
        overwritting perform_update for specific action and its logic
        removes all the requests active/ boarded from the elevator as fulfilled 
        marks the elevator under maintaince and takes it to ground floor.
        """
        instance = serializer.instance
        instance.is_under_maintainance = True
        instance.current_floor = 0
        instance.next_floor = None
        instance.elevator_status = ELEVATOR_STATUS_CHOICES.IDLE
        instance.door_status = DOOR_STATUS_CHOICES.CLOSED
        instance.save()
        
        remove_people_from_undermaintainance_elevator(instance.id)
    

    def perform_update_doors(self, serializer):
        """
        opens / closes  doors of the elevator
        """
        instance = serializer.instance
        instance.door_status = DOOR_STATUS_CHOICES.OPEN if instance.door_status == DOOR_STATUS_CHOICES.CLOSED else DOOR_STATUS_CHOICES.CLOSED
        instance.save()


class RequestViewSet(viewsets.ModelViewSet):
    """
    Api to request an elevator for service by a user
    This api will assign an optimal Elevator to this request according to the business logic.
    """
    queryset = Request.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'request_id'

    def get_serializer_class(self):
        """
        Return different serializers based on the action being performed.
        """
        if self.action == 'update':
            return AddDestianationFloorSerialzer
        else:
            return RequestSerializer

    def perform_create(self, serializer):
        """
        Api to create a new elevator request and assign optimal elevator
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
        # if an eleavtor at same floor was assigned mark the request as boarded
        if elevator_assigned_obj.current_floor == pickup_floor:
            serializer.validated_data['status'] = REQUEST_STATUS_CHOICES.BOARDED
        
        serializer.save()

        return Response(serializer.data)


    def update(self, request, *args, **kwargs):
        """
        Api to add destination floor to requests
        """
        allowed_fields = ['destination_floor']
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if instance.elevator.current_floor != instance.pick_up_floor:
            raise ValidationError('Your elevator has not arrived yet please wait.')
        if instance.pick_up_floor == instance.destination_floor:
            raise ValidationError('current floor and destination floor cant be same')

        for field in allowed_fields:
            if field in request.data:
                setattr(instance, field, request.data[field])

        instance.save()

        return Response(serializer.data)

