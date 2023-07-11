from rest_framework.generics import CreateAPIView, UpdateAPIView, ListAPIView
from elevator.serializers import RequestSerializer
from rest_framework.response import Response
from .models import Elevator, Request
from rest_framework.exceptions import ValidationError
from django.db.models import F

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
    # serializer_class = MoveElevatorSerializer

    def perform_update(self, serializer):
        """
        Updates the Elevators data for next_floor, current_floor, doors_status, and elevator status
        """

        next_floor = serializer.validated_data['next_floor']
        # if there are no floors raise EXCEPTION
        if next_floor is None:
            raise ValidationError('No requests for this elevator at this time')
        
        # all requests for current elevator
        all_requests = get_all_requests_for_elevator(elevator_id=serializer.validated_data['id'])
        requests_with_no_destinations = all_requests.filter(
            pick_up_floor=serializer.validated_data['pick_up_floor'],
            destination_floor__is_null=True
        )
        if requests_with_no_destinations:
            raise ValidationError('Some users have not choosen their destination floor plase choose.')
    
        #  current floor of the elevator will be next floor after moving (assumed reflects instantly)
        serializer.validated_data['current_floor'] = next_floor
        elevator_status = serializer.validated_data['elevator_status']
        # filtering requests who have their destination at current floor
        all_requests_fulfilled = all_requests.filter(destination_floor=next_floor)
        all_requests_fulfilled.update(status='Fulfilled')
        # remaining requests
        all_requests_pending = all_requests.filter(status='Active')
        # If no request is pending for elevator mark status idle
        if not all_requests_pending:
            serializer.validated_data['elevator_status'] = 'Idle'
            serializer.validated_data['next_floor'] = None
        else:
            # Getting the nearest floor to reach in case where elevator is already going up / Down  or Is Idle 
            nearest_floor_above = all_requests.filter(pickup_floor__gt=next_floor).order_by('pickup_floor').first()
            nearest_floor_down = all_requests.filter(pickup_floor__lt=next_floor).order_by('-pickup_floor').first()
            if elevator_status == 'Going_up' or elevator_status == 'Idle':
                serializer.validated_data['next_floor'] = (
                    nearest_floor_above.pickup_floor if nearest_floor_above else nearest_floor_down.pickup_floor
                )
            else:
                serializer.validated_data['next_floor'] = (
                    nearest_floor_down.pickup_floor if nearest_floor_down else nearest_floor_above.pickup_floor
                )
            
            serializer.validated_data['elevator_status'] = (
                'Going_up' if serializer.validated_data['next_floor'] > serializer.validated_data['current_floor']
                else 'Going_down'
            )

        serializer.save()
        return Response({'Message': "Elevator has arrived at {next_floor}", 'data': serializer.data})


class GetActiveRequestsForElevator(ListAPIView):
    """
    View to return all active request for an elevator
    """
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    lookup_url_kwarg = 'id'
    
    def get_queryset(self):
        """
        returns queryset of all active requests for an elevator
        """
        elevator_id = self.kwargs.get(self.lookup_url_kwarg)
        return get_all_requests_for_elevator(elevator_id=elevator_id)


