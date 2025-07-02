from django.contrib import admin
from django.forms import ModelForm, ModelChoiceField
from django import forms
from bson import ObjectId
from .models import Sport, Court, TimeSlot, Booking

class ObjectIdModelChoiceField(ModelChoiceField):
    """Custom field to handle ObjectId foreign keys properly"""
    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            if isinstance(value, str):
                # Try to convert string to ObjectId
                if len(value) == 24:  # ObjectId string length
                    return self.queryset.get(_id=ObjectId(value))
                else:
                    # Regular primary key
                    return self.queryset.get(pk=value)
            return super().to_python(value)
        except (self.queryset.model.DoesNotExist, ValueError):
            raise forms.ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )

class TimeSlotForm(ModelForm):
    class Meta:
        model = TimeSlot
        fields = ['hour']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hour'].help_text = "Enter hour in 24-hour format (7-22 for 7 AM to 10 PM)"
        self.fields['hour'].widget.attrs['min'] = 7
        self.fields['hour'].widget.attrs['max'] = 22

class CourtForm(ModelForm):
    sport = ModelChoiceField(
        queryset=Sport.objects.all(),
        empty_label="Select a sport",
        to_field_name='id'  # Use the primary key field
    )
    
    class Meta:
        model = Court
        fields = ['sport', 'name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sport'].queryset = Sport.objects.all()

class BookingForm(ModelForm):
    court = ObjectIdModelChoiceField(
        queryset=Court.objects.all().select_related('sport'),
        empty_label="Select a court"
    )
    time_slot = ObjectIdModelChoiceField(
        queryset=TimeSlot.objects.all().order_by('hour'),
        empty_label="Select a time slot"
    )
    
    class Meta:
        model = Booking
        fields = ['court', 'time_slot', 'date', 'status', 'user']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up court choices with better display
        self.fields['court'].queryset = Court.objects.all().select_related('sport')
        self.fields['court'].label_from_instance = lambda obj: f"{obj.sport.name} - {obj.name}"
        
        # Set up time slot choices with formatted display
        self.fields['time_slot'].queryset = TimeSlot.objects.all().order_by('hour')
        self.fields['time_slot'].label_from_instance = lambda obj: obj.formatted_slot
        
        # Set default date to today
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.now().date()

@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion if courts exist for this sport
        if obj and obj.courts.exists():
            return False
        return super().has_delete_permission(request, obj)

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    form = TimeSlotForm
    list_display = ('get_id', 'hour', 'formatted_slot')
    ordering = ('hour',)
    list_filter = ('hour',)
    
    def get_id(self, obj):
        return str(obj._id)
    get_id.short_description = 'ID'
    
    def formatted_slot(self, obj):
        return obj.formatted_slot
    formatted_slot.short_description = 'Time Slot'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion if bookings exist for this time slot
        if obj and hasattr(obj, 'booking_set') and obj.booking_set.exists():
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    form = CourtForm
    list_display = ('get_id', 'name', 'sport')
    list_filter = ('sport',)
    search_fields = ('name', 'sport__name')
    ordering = ('sport', 'name')
    
    def get_id(self, obj):
        return str(obj._id)
    get_id.short_description = 'ID'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion if bookings exist for this court
        if obj and hasattr(obj, 'booking_set') and obj.booking_set.exists():
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('get_id', 'get_court_display', 'get_time_slot_display', 'date', 'status', 'user', 'updated_at')
    list_filter = ('status', 'date', 'court__sport', 'time_slot__hour')
    search_fields = ('court__name', 'user__username', 'court__sport__name')
    date_hierarchy = 'date'
    ordering = ('-date', 'time_slot__hour', 'court__sport', 'court__name')
    
    def get_id(self, obj):
        return str(obj._id)
    get_id.short_description = 'ID'
    
    def get_court_display(self, obj):
        return f"{obj.court.sport.name} - {obj.court.name}"
    get_court_display.short_description = 'Court'
    
    def get_time_slot_display(self, obj):
        return obj.time_slot.formatted_slot
    get_time_slot_display.short_description = 'Time Slot'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'court', 'court__sport', 'time_slot', 'user'
        )
    
    fieldsets = (
        ('Booking Details', {
            'fields': ('court', 'time_slot', 'date', 'status')
        }),
        ('User Information', {
            'fields': ('user',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        """Override save to handle potential duplicate bookings"""
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            # Handle unique constraint violations gracefully
            from django.contrib import messages
            messages.error(request, f"Error saving booking: {str(e)}")

# Custom admin site configuration
admin.site.site_header = "IITB Sports Facility Admin"
admin.site.site_title = "Sports Booking Admin"
admin.site.index_title = "Sports Facility Management"

# Add some custom actions
def mark_as_available(modeladmin, request, queryset):
    queryset.update(status='available')
mark_as_available.short_description = "Mark selected bookings as available"

def mark_as_booked(modeladmin, request, queryset):
    queryset.update(status='booked')
mark_as_booked.short_description = "Mark selected bookings as booked"

def mark_as_maintenance(modeladmin, request, queryset):
    queryset.update(status='maintenance')
mark_as_maintenance.short_description = "Mark selected bookings as maintenance"

# Add actions to BookingAdmin
BookingAdmin.actions = [mark_as_available, mark_as_booked, mark_as_maintenance]