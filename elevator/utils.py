from rest_framework.exceptions import ValidationError
from django.db.models.functions import Coalesce
from django.db.models import Subquery, OuterRef, Count, IntegerField, F, Value, Q, Func

from elevator.models import Elevator, Request

def get_most_suitable_elevator(pickup_floor: int):
    """
    returns most suitable elevator_id for an elevator request based on the business logic
    """
    request_count_subquery = Request.objects.filter(
        elevator_id=OuterRef('id'),
        status='Active'
    ).annotate(request_count=Coalesce(Count('id'), Value(0))).values('request_count')[:1]

    elevators_with_active_request_count = Elevator.objects.annotate(
        request_count = Coalesce(
        Subquery(request_count_subquery, output_field=IntegerField()), Value(0)
        ),
        floor_difference=Func(F('current_floor') - pickup_floor, function='ABS')
    )

    if not elevators_with_active_request_count:
        raise ValidationError('System is not initialized yet')

    # assign elevator with minimal requests active 
    elevator_id = None
    #  check if any elevator is at the same floor and status is halt
    elevators_at_current_floor = elevators_with_active_request_count.filter(current_floor=pickup_floor).order_by('request_count')
    if elevators_at_current_floor:
        elevator_id = elevators_at_current_floor.first().id
    
    #  check if some elevator is having no request
    if not elevator_id:
        elevators_with_no_request = elevators_with_active_request_count.filter(elevator_status='Idle').order_by('floor_difference')
        elevator_id = elevators_with_no_request.first().id if elevators_with_no_request else None
    
    #  check if there is some elevator on floor above and comming down or floor below and going up
    #  take the nearest one.
    if not elevator_id:
        elevators_below_and_comming_up = elevators_with_active_request_count.filter(
            Q(next_floor__gte=pickup_floor) | Q(next_floor=0),
            current_floor__lt=pickup_floor
        ).order_by('floor_difference', 'request_count')

        elevators_above_and_comming_down = elevators_with_active_request_count.filter(
            Q(next_floor__lte=pickup_floor) | Q(next_floor=0),
            current_floor__gt=pickup_floor,
        ).order_by('floor_difference', 'request_count')
        # when there are elevators below and above
        if elevators_below_and_comming_up and elevators_above_and_comming_down:
            #  if both are at same distance from pickup floor take the one with least request
            if elevators_below_and_comming_up.first().floor_difference == elevators_above_and_comming_down.first().floor_difference:
                elevator_id = (
                    elevators_below_and_comming_up.first().id if elevators_below_and_comming_up.first().request_count <= elevators_above_and_comming_down.first().request_count
                    else elevators_above_and_comming_down.first().id
                )
            else:
                elevator_id = (
                    elevators_below_and_comming_up.first().id if elevators_below_and_comming_up.first().request_count <= elevators_above_and_comming_down.first().request_count 
                    else elevators_above_and_comming_down.first().id
                )
        elif not (elevator_id or elevators_below_and_comming_up):
            elevator_id = elevators_above_and_comming_down.first().id

        else:
            elevator_id = elevators_below_and_comming_up.first().id
    
    return elevator_id

def get_all_requests_for_elevator(elevator_id: int):
    """
    returns queryset of all active requests for an elevator
    """
    return Request.objects.filter(elevator_id=elevator_id, status='Active')


