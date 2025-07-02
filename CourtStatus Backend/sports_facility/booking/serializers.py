from rest_framework import serializers
from .models import Sport, Court, TimeSlot, Booking

class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ['id', 'name']

class CourtSerializer(serializers.ModelSerializer):
    sport_name = serializers.CharField(source='sport.name', read_only=True)
    id = serializers.SerializerMethodField()
    
    class Meta:
        model = Court
        fields = ['id', 'name', 'sport', 'sport_name']
    
    def get_id(self, obj):
        return str(obj._id)

class TimeSlotSerializer(serializers.ModelSerializer):
    formatted_slot = serializers.ReadOnlyField()
    id = serializers.SerializerMethodField()
    
    class Meta:
        model = TimeSlot
        fields = ['id', 'hour', 'formatted_slot']
    
    def get_id(self, obj):
        return str(obj._id)

class BookingSerializer(serializers.ModelSerializer):
    court_name = serializers.CharField(source='court.name', read_only=True)
    sport_name = serializers.CharField(source='court.sport.name', read_only=True)
    time_slot_formatted = serializers.CharField(source='time_slot.formatted_slot', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    id = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'court', 'court_name', 'sport_name', 
            'time_slot', 'time_slot_formatted', 'date', 
            'status', 'user', 'user_name', 'created_at', 'updated_at'
        ]
    
    def get_id(self, obj):
        return str(obj._id)
