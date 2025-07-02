from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import JsonResponse
from bson import ObjectId
import datetime
import json

from .models import Sport, Court, TimeSlot, Booking, BookingStatus
from .serializers import SportSerializer, CourtSerializer, TimeSlotSerializer, BookingSerializer

@api_view(['GET'])
def court_status_api(request):
    """API endpoint for getting court status - Frontend compatible"""
    sport_id = request.query_params.get('sport', None)
    date_str = request.query_params.get('date', timezone.now().date().isoformat())

    try:
        booking_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=400)

    # Get sport or default to first available
    if not sport_id:
        first_sport = Sport.objects.first()
        if first_sport:
            sport_id = first_sport.id
        else:
            return Response({'error': 'No sports available'}, status=404)

    # Ensure we have time slots
    if not TimeSlot.objects.exists():
        TimeSlot.create_default_slots()

    # Get all required data
    sports_data = SportSerializer(Sport.objects.all(), many=True).data
    time_slots = TimeSlot.objects.all().order_by('hour')
    courts = Court.objects.filter(sport__id=sport_id)
    
    # Get all bookings for the selected sport and date
    bookings = Booking.objects.filter(
        court__sport__id=sport_id,
        date=booking_date
    ).select_related('court', 'time_slot')

    # Build court data structure matching frontend expectations
    court_data = []
    for court in courts:
        court_info = {
            'id': str(court._id),
            'name': court.name,
            'slots': {}
        }
        
        # Create slot structure for each time slot - use sequential IDs for frontend
        for i, slot in enumerate(time_slots, 1):
            court_info['slots'][str(i)] = {
                'id': str(i),
                'time': slot.formatted_slot,
                'status': 'available'
            }

        # Update with actual booking statuses
        court_bookings = bookings.filter(court___id=court._id)
        for booking in court_bookings:
            # Find matching slot by hour and map to frontend ID
            for i, slot in enumerate(time_slots, 1):
                if slot._id == booking.time_slot._id:
                    slot_id = str(i)
                    if slot_id in court_info['slots']:
                        court_info['slots'][slot_id]['status'] = booking.status
                    break

        court_data.append(court_info)

    # Build time slots data for frontend
    time_slots_data = []
    for i, slot in enumerate(time_slots, 1):
        time_slots_data.append({
            'id': i,
            'formatted_slot': slot.formatted_slot
        })

    response_data = {
        'date': date_str,
        'currentTime': timezone.now().strftime('%I:%M %p'),
        'sports': sports_data,
        'selectedSport': sport_id,
        'timeSlots': time_slots_data,
        'courts': court_data
    }

    return Response(response_data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_booking_api(request):
    """API endpoint for updating booking status - Frontend compatible"""
    court_id = request.data.get('courtId')
    time_slot_id = request.data.get('timeSlotId')
    new_status = request.data.get('status')
    date_str = request.data.get('date', timezone.now().date().isoformat())

    if not all([court_id, time_slot_id, new_status]):
        return Response({
            'error': 'Missing required fields: courtId, timeSlotId, status'
        }, status=400)

    # Validate status
    valid_statuses = [choice[0] for choice in BookingStatus.choices]
    if new_status not in valid_statuses:
        return Response({
            'error': f'Invalid status. Valid options: {valid_statuses}'
        }, status=400)

    try:
        booking_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=400)

    # Convert frontend slot ID to actual time slot
    try:
        frontend_slot_id = int(time_slot_id)
        time_slots = TimeSlot.objects.all().order_by('hour')
        time_slot = list(time_slots)[frontend_slot_id - 1]  # Convert to 0-based index
        
        court_object_id = ObjectId(court_id)
        court = Court.objects.get(_id=court_object_id)
    except (Court.DoesNotExist, TimeSlot.DoesNotExist, IndexError, ValueError, Exception) as e:
        return Response({'error': f'Invalid court or time slot: {str(e)}'}, status=400)

    try:
        if new_status == 'available':
            # Delete existing booking
            deleted_count = Booking.objects.filter(
                court___id=court_object_id,
                time_slot___id=time_slot._id,
                date=booking_date
            ).delete()[0]
            
            response_booking = {
                'court': court.name,
                'time_slot': time_slot.formatted_slot,
                'date': booking_date.isoformat(),
                'status': new_status,
                'user': request.user.username,
                'action': 'deleted' if deleted_count > 0 else 'no_change'
            }
        else:
            # Create or update booking
            booking, created = Booking.objects.update_or_create(
                court___id=court_object_id,
                time_slot___id=time_slot._id,
                date=booking_date,
                defaults={
                    'status': new_status,
                    'user': request.user
                }
            )
            
            response_booking = {
                'id': str(booking._id) if hasattr(booking, '_id') else None,
                'court': court.name,
                'time_slot': time_slot.formatted_slot,
                'date': booking_date.isoformat(),
                'status': new_status,
                'user': request.user.username,
                'action': 'created' if created else 'updated'
            }

        return Response({
            'success': True,
            'booking': response_booking
        })

    except Exception as e:
        return Response({
            'error': f'Failed to update booking: {str(e)}'
        }, status=500)

# Include all other view functions from the previous views.py
class SportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sport.objects.all()
    serializer_class = SportSerializer

class TimeSlotViewSet(viewsets.ModelViewSet):
    queryset = TimeSlot.objects.all().order_by('hour')
    serializer_class = TimeSlotSerializer

@api_view(['GET'])
def sports_list_api(request):
    sports = Sport.objects.all()
    return Response(SportSerializer(sports, many=True).data)

@api_view(['GET'])
def time_slots_api(request):
    if not TimeSlot.objects.exists():
        TimeSlot.create_default_slots()
    
    time_slots = TimeSlot.objects.all().order_by('hour')
    return Response(TimeSlotSerializer(time_slots, many=True).data)

@api_view(['GET'])
def debug_data_api(request):
    return Response({
        'sports_count': Sport.objects.count(),
        'courts_count': Court.objects.count(),
        'time_slots_count': TimeSlot.objects.count(),
        'bookings_count': Booking.objects.count(),
        'time_slots': [
            {
                'id': str(slot._id),
                'hour': slot.hour,
                'formatted': slot.formatted_slot
            } for slot in TimeSlot.objects.all().order_by('hour')
        ]
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_sample_data(request):
    # Create sports
    sports_data = [
        {'id': 'badminton', 'name': 'Badminton'},
        {'id': 'volleyball', 'name': 'Volleyball'},
        {'id': 'basketball', 'name': 'Basketball'},
        {'id': 'squash', 'name': 'Squash'},
        {'id': 'table-tennis', 'name': 'Table Tennis'},
        {'id': 'cricket', 'name': 'Cricket'},
    ]
    
    for sport_data in sports_data:
        Sport.objects.get_or_create(
            id=sport_data['id'],
            defaults={'name': sport_data['name']}
        )
    
    # Create time slots
    TimeSlot.create_default_slots()
    
    # Create sample courts for each sport
    for sport_data in sports_data:
        try:
            sport = Sport.objects.get(id=sport_data['id'])
            for i in range(1, 5):  # Create 4 courts per sport
                Court.objects.get_or_create(
                    sport=sport,
                    name=f'{sport.name} Court {i}' if sport.name != 'Cricket' else f'Pitch-{i}'
                )
        except Sport.DoesNotExist:
            continue
    
    return Response({
        'success': True,
        'message': 'Sample data created successfully'
    })
