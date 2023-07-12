from rest_framework.exceptions import ValidationError
from django.db.models.functions import Coalesce
from django.db.models import Subquery, OuterRef, Count, IntegerField, F, Value, Q, Func

from elevator.models import ELEVATOR_STATUS_CHOICES, REQUEST_STATUS_CHOICES, Elevator, Request

def get_most_suitable_elevator(pickup_floor: int):
    """
    returns most suitable elevator_id for an elevator request based on the business logic
    """
    request_count_subquery = Request.objects.filter(
        elevator_id=OuterRef('id'), 
        status__in=[REQUEST_STATUS_CHOICES.ACTIVE, REQUEST_STATUS_CHOICES.BOARDED]
    ).annotate(request_count=Coalesce(Count('id'), Value(0))).values('request_count')[:1]

    elevators_with_active_request_count = Elevator.objects.filter(is_under_maintainance=False).annotate(
        request_count = Coalesce(
        Subquery(request_count_subquery, output_field=IntegerField()), Value(0)
        ),
        floor_difference=Func(F('current_floor') - pickup_floor, function='ABS')
    )

    if not elevators_with_active_request_count:
        raise ValidationError('System is not initialized yet or all elevators are under maintainance')

    # assign elevator with minimal requests active 
    elevator_id = None
    #  check if any elevator is at the same floor and status is halt
    elevators_at_current_floor = elevators_with_active_request_count.filter(current_floor=pickup_floor).order_by('request_count')
    if elevators_at_current_floor:
        elevator_id = elevators_at_current_floor.first().id
    
    #  check if some elevator is having no request
    if not elevator_id:
        elevators_with_no_request = elevators_with_active_request_count.filter(elevator_status=ELEVATOR_STATUS_CHOICES.IDLE).order_by('floor_difference')
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
            #  when only elevators above current floor are present
            elevator_id = elevators_above_and_comming_down.first().id

        else:
            #  when only below elevators are present
            elevator_id = elevators_below_and_comming_up.first().id
    
    return elevator_id

def get_all_requests_for_elevator(elevator_id: int):
    """
    returns queryset of all active requests for an elevator
    """
    return Request.objects.filter(elevator_id=elevator_id, status__in=[REQUEST_STATUS_CHOICES.ACTIVE, REQUEST_STATUS_CHOICES.BOARDED])

def get_floors_above_below_to_board_and_deboard(all_requests_pending, current_floor: int):
    """
    returns 4 objects 
    1. nearest_floor_above_to_board -> nearest floor above to pickup user
    2. nearest_floor_above_to_deboard -> nearest floor above to deoard user
    3. nearest_floor_down_to_board ->  nearest floor down to pickup user
    4. nearest_floor_down_to_deboard -> nearest floor above to deoard user
    """
    nearest_floor_above_to_board = all_requests_pending.filter(pick_up_floor__gt=current_floor, status=REQUEST_STATUS_CHOICES.ACTIVE).order_by('pick_up_floor').first()
    nearest_floor_above_to_deboard = all_requests_pending.filter(destination_floor__gt=current_floor, status=REQUEST_STATUS_CHOICES.BOARDED).order_by('destination_floor').first()

    nearest_floor_down_to_board = all_requests_pending.filter(pick_up_floor__lt=current_floor, status=REQUEST_STATUS_CHOICES.ACTIVE).order_by('-pick_up_floor').first()
    nearest_floor_down_to_deboard = all_requests_pending.filter(destination_floor__lt=current_floor, status=REQUEST_STATUS_CHOICES.BOARDED).order_by('-destination_floor').first()

    return nearest_floor_above_to_board, nearest_floor_above_to_deboard, nearest_floor_down_to_board, nearest_floor_down_to_deboard

def get_next_floor(nearest_floor_above_to_board, nearest_floor_above_to_deboard, nearest_floor_down_to_board, nearest_floor_down_to_deboard, elevator_status: str, current_floor: int):
    """
    returns the next floor the elevator will be going to
    """
    next_floor = None
    if elevator_status == ELEVATOR_STATUS_CHOICES.IDLE and not(nearest_floor_above_to_deboard or nearest_floor_down_to_deboard):
        # when elevator was at rest and someone boarded  it can be above or below or both
        if nearest_floor_above_to_board and nearest_floor_down_to_board:
            next_floor = (
                nearest_floor_above_to_board.pick_up_floor 
                if abs(nearest_floor_above_to_board.pick_up_floor - current_floor) <= abs(nearest_floor_down_to_board.pick_up_floor - current_floor)
                else nearest_floor_down_to_board.pick_up_floor
            )
        else:
            next_floor = (
                nearest_floor_above_to_board.pick_up_floor 
                if nearest_floor_above_to_board
                else nearest_floor_down_to_board.pick_up_floor
            )
    elif elevator_status == ELEVATOR_STATUS_CHOICES.IDLE and (nearest_floor_above_to_deboard or nearest_floor_down_to_deboard):
        # when elevator was idle and someone boarded at current floor and has to go up or down.
        if nearest_floor_above_to_deboard and nearest_floor_down_to_deboard:
            next_floor = (
                nearest_floor_above_to_deboard.destination_floor 
                if abs(nearest_floor_above_to_deboard.destination_floor - current_floor) <= abs(nearest_floor_down_to_deboard.destination_floor - current_floor)
                else nearest_floor_down_to_deboard.destination_floor
            )
        else:
            next_floor = (
                nearest_floor_above_to_deboard.destination_floor 
                if nearest_floor_above_to_deboard
                else nearest_floor_down_to_deboard.destination_floor
            )
    elif elevator_status == ELEVATOR_STATUS_CHOICES.GOING_UP:
        # check which is someone is there to board/de board up if both then choose the nearset floor
        if not (nearest_floor_above_to_board or nearest_floor_above_to_deboard):
            if nearest_floor_down_to_board and nearest_floor_down_to_deboard:
                next_floor = (
                    nearest_floor_down_to_board.pick_up_floor 
                    if abs(nearest_floor_down_to_board.pick_up_floor - current_floor) <= abs(nearest_floor_down_to_deboard.destination_floor - current_floor)
                    else nearest_floor_down_to_deboard.destination_floor
                )
            else:
                next_floor = nearest_floor_down_to_board.pick_up_floor if nearest_floor_down_to_board else nearest_floor_down_to_deboard.destination_floor
        # if there are requests to board and deboard above then will reach the first closest floor.
        elif nearest_floor_above_to_board and nearest_floor_above_to_deboard:
            next_floor = (
                nearest_floor_above_to_board.pick_up_floor 
                if abs(nearest_floor_above_to_board.pick_up_floor - current_floor) <= abs(nearest_floor_above_to_deboard.destination_floor - current_floor)
                else nearest_floor_above_to_deboard.destination_floor
            )
        else:
            next_floor = (
                nearest_floor_above_to_board.pick_up_floor 
                if nearest_floor_above_to_board else nearest_floor_above_to_deboard.destination_floor
            )
    else:
        # case when list is going down we will take all requests which have to board or deboard till none are left in down side
        if not (nearest_floor_down_to_board or nearest_floor_down_to_deboard):
            if nearest_floor_above_to_board and nearest_floor_above_to_deboard:
                next_floor = (
                nearest_floor_above_to_board.pick_up_floor 
                    if abs(nearest_floor_above_to_board.pick_up_floor - current_floor) <= abs(nearest_floor_above_to_deboard.destination_floor - current_floor)
                    else nearest_floor_above_to_deboard.destination_floor
                )
            else:
                next_floor = nearest_floor_above_to_board.pick_up_floor if nearest_floor_above_to_board else nearest_floor_above_to_deboard.destination_floor

        elif nearest_floor_down_to_board and nearest_floor_down_to_deboard:
            next_floor = (
                nearest_floor_down_to_board.pick_up_floor 
                if abs(nearest_floor_down_to_board.pick_up_floor - current_floor) <= abs(nearest_floor_down_to_deboard.destination_floor - current_floor)
                else nearest_floor_down_to_deboard.destination_floor
            )
        else:
            next_floor = (
                nearest_floor_down_to_board.pick_up_floor 
                if nearest_floor_down_to_board else nearest_floor_down_to_deboard.destination_floor
            )
    
    return next_floor 

def get_next_floor_for_elevator(all_requests, elevator_status, current_floor):
    """
    returns next floor the elevator will e going to
    """
    all_requests_pending = all_requests.filter(status__in=[REQUEST_STATUS_CHOICES.ACTIVE, REQUEST_STATUS_CHOICES.BOARDED])
    if not all_requests_pending:
        return None

    nearest_floor_above_to_board, nearest_floor_above_to_deboard, nearest_floor_down_to_board, nearest_floor_down_to_deboard = (
        get_floors_above_below_to_board_and_deboard(all_requests_pending, current_floor)
    )
    #  if there are no requests then return next floor as null
    if not(nearest_floor_above_to_board or nearest_floor_above_to_deboard or nearest_floor_down_to_board or nearest_floor_down_to_deboard):
        return None
    #  getting the next floor
    return get_next_floor(nearest_floor_above_to_board, nearest_floor_above_to_deboard, nearest_floor_down_to_board, nearest_floor_down_to_deboard, elevator_status, current_floor)

def remove_people_from_undermaintainance_elevator(elevator_id: int):
    """
    marks all elevator requests for this elevator as full filled 
    user will have to again request an elevator
    """
    all_request_active_or_boarded = get_all_requests_for_elevator(elevator_id)
    all_request_active_or_boarded.update(status=REQUEST_STATUS_CHOICES.FULFILLED)

