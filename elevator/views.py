from rest_framework.generics import CreateAPIView, UpdateAPIView, ListAPIView
from elevator.serializers import DoorStatusSerializer, MoveElevatorSerializer, RequestSerializer
from rest_framework.response import Response
from .models import Elevator, Request
from rest_framework.exceptions import ValidationError
from django.db.models import F, Q

from elevator.utils import get_all_requests_for_elevator, get_most_suitable_elevator

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
        if elevator_assigned_obj.elevator_status == 'Idle':
            elevator_assigned_obj.elevator_status= (
                'Going_up' if (
                    pickup_floor >= elevator_assigned_obj.current_floor and
                    pickup_floor < elevator_assigned_obj.systems_max_floor
                )
                else 'Going_down'
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

    def perform_update(self, serializer):
        """
        Updates the Elevators data for next_floor, current_floor, doors_status, and elevator status
        """
        instance = serializer.instance    
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)
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
        all_requests_boarded = all_requests.filter(pick_up_floor=instance.current_floor)
        all_requests_boarded.update(status='Boarded')
        # filtering requests who have their destination at current floor
        all_requests_fulfilled = all_requests.filter(destination_floor=instance.current_floor)
        all_requests_fulfilled.update(status='Fulfilled')
        all_requests_pending = all_requests.filter(status__in=['Active', 'Boarded'])
        # If no request is pending for elevator mark status idle
        if not all_requests_pending:
            instance.next_floor = None
            instance.elevator_status = 'Idle'
            instance.save()
            raise ValidationError('There are no request for this elevator')
        else:
            # Getting the nearest floor to reach in case where elevator is already going up / Down  or Is Idle 
            nearest_floor_above_to_board = all_requests_pending.filter(pick_up_floor__gt=instance.current_floor, status='Active').order_by('pick_up_floor').first()
            nearest_floor_above_to_deboard = all_requests_pending.filter(destination_floor__gt=instance.current_floor, status='Boarded').order_by('destination_floor').first()

            nearest_floor_down_to_board = all_requests_pending.filter(pick_up_floor__lt=instance.current_floor, status='Active').order_by('-pick_up_floor').first()
            nearest_floor_down_to_deboard = all_requests_pending.filter(destination_floor__lt=instance.current_floor, status='Boarded').order_by('-destination_floor').first()

            if not (nearest_floor_above_to_board or nearest_floor_above_to_deboard or nearest_floor_down_to_board or nearest_floor_down_to_deboard):
                instance.current_floor = instance.next_floor
                instance.next_floor = None
                instance.elevator_status = 'Idle'
            else:
                if elevator_status == 'Idle':
                    if nearest_floor_above_to_board and nearest_floor_down_to_board:
                        instance.next_floor = (
                            nearest_floor_above_to_board.pick_up_floor 
                            if abs(nearest_floor_above_to_board.pick_up_floor - instance.current_floor) <= abs(nearest_floor_down_to_board.pick_up_floor - instance.current_floor)
                            else nearest_floor_down_to_board.pick_up_floor
                        )
                    else:
                        instance.next_floor = (
                            nearest_floor_above_to_board.pick_up_floor 
                            if nearest_floor_above_to_board
                            else nearest_floor_down_to_board.pick_up_floor
                        )
                elif elevator_status == 'Going_up':
                    # check which is someone is there to board/de board up if both then choose the nearset floor
                    if not (nearest_floor_above_to_board or nearest_floor_above_to_deboard):
                        if nearest_floor_down_to_board and nearest_floor_down_to_deboard:
                            instance.next_floor = (
                                nearest_floor_down_to_board.pick_up_floor 
                                if abs(nearest_floor_down_to_board.pick_up_floor - instance.current_floor) <= abs(nearest_floor_down_to_deboard.destination_floor - instance.current_floor)
                                else nearest_floor_down_to_deboard.destination_floor
                            )
                        else:
                            instance.next_floor = nearest_floor_down_to_board.pick_up_floor if nearest_floor_down_to_board else nearest_floor_down_to_deboard.destination_floor
                        
                    elif nearest_floor_above_to_board and nearest_floor_above_to_deboard:
                        instance.next_floor = (
                            nearest_floor_above_to_board.pick_up_floor 
                            if abs(nearest_floor_above_to_board.pick_up_floor - instance.current_floor) <= abs(nearest_floor_above_to_deboard.destination_floor - instance.current_floor)
                            else nearest_floor_above_to_deboard.destination_floor
                        )
                    else:
                        instance.next_floor = (
                            nearest_floor_above_to_board.pick_up_floor 
                            if nearest_floor_above_to_board else nearest_floor_above_to_deboard.destination_floor
                        )
                else:
                    if not (nearest_floor_down_to_board or nearest_floor_down_to_deboard):
                        if nearest_floor_above_to_board and nearest_floor_above_to_deboard:
                            instance.next_floor = (
                            nearest_floor_above_to_board.pick_up_floor 
                                if abs(nearest_floor_above_to_board.pick_up_floor - instance.current_floor) <= abs(nearest_floor_above_to_deboard.destination_floor - instance.current_floor)
                                else nearest_floor_above_to_deboard.destination_floor
                            )
                        else:
                            instance.next_floor = nearest_floor_above_to_board.pick_up_floor if nearest_floor_above_to_board else nearest_floor_above_to_deboard.destination_floor

                    elif nearest_floor_down_to_board and nearest_floor_down_to_deboard:
                        instance.next_floor = (
                            nearest_floor_down_to_board.pick_up_floor 
                            if abs(nearest_floor_down_to_board.pick_up_floor - instance.current_floor) <= abs(nearest_floor_down_to_deboard.destination_floor - instance.current_floor)
                            else nearest_floor_down_to_deboard.destination_floor
                        )
                    else:
                        instance.next_floor = (
                            nearest_floor_down_to_board.pick_up_floor 
                            if nearest_floor_down_to_board else nearest_floor_down_to_deboard.destination_floor
                        )
            #  Marking elevator for up or down direction
            instance.elevator_status = (
                'Going_up' if instance.next_floor > instance.current_floor
                else 'Going_down'
            )
            instance.current_floor = instance.next_floor
            instance.save()
        return Response({'Message': "Elevator has arrived at {next_floor}", 'data': serializer.data})


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


class UnderMaintainanceElevator(UpdateAPIView):
    """
    View to mark elevator under maintainance and deboard all members at current floor
    also marl all active requests for this elevator as fulfilled and user can request fro new elevator
    """
    def perform_update(self, serializer):
        return super().perform_update(serializer)
    

class OpenCloseElevatorDoors(UpdateAPIView):
    """
    Opens/closes the doors of an elevator
    """
    queryset = Elevator.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'elevator_id'
    serializer_class = DoorStatusSerializer

    def perform_update(self, serializer):
        instance = serializer.instance
        instance.door_status = 'Open' if instance.door_status == 'Closed' else 'Closed'
        instance.save()

