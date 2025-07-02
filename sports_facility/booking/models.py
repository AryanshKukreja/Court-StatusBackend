from djongo import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

class Sport(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'sports'

class TimeSlot(models.Model):
    _id = models.ObjectIdField()
    hour = models.IntegerField(unique=True)
    
    @property
    def id(self):
        return str(self._id)
    
    @property
    def formatted_slot(self):
        hour_12 = self.hour % 12
        if hour_12 == 0:
            hour_12 = 12
        am_pm = "AM" if self.hour < 12 else "PM"
        return f"{hour_12}:00 {am_pm}"
    
    def __str__(self):
        return self.formatted_slot

    class Meta:
        db_table = 'timeslots'
        ordering = ['hour']

    @classmethod
    def create_default_slots(cls):
        for hour in range(7, 23):
            cls.objects.get_or_create(hour=hour)

class Court(models.Model):
    _id = models.ObjectIdField()
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='courts')
    name = models.CharField(max_length=100)

    @property
    def id(self):
        return str(self._id)

    def __str__(self):
        return f"{self.sport.name} - {self.name}"

    class Meta:
        db_table = 'courts'

class BookingStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    BOOKED = 'booked', 'Booked'
    MAINTENANCE = 'maintenance', 'Maintenance'
    RESERVED = 'reserved', 'Reserved'

class Booking(models.Model):
    _id = models.ObjectIdField()
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    date = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.BOOKED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def id(self):
        return str(self._id)
    
    class Meta:
        db_table = 'bookings'
        indexes = [
            models.Index(fields=['court', 'time_slot', 'date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['court', 'time_slot', 'date'],
                name='unique_booking_per_court_time_date'
            )
        ]
    
    def save(self, *args, **kwargs):
        """Enhanced save method to handle uniqueness properly"""
        if not self.pk:  # Only for new bookings
            # Check for existing booking
            existing = Booking.objects.filter(
                court=self.court,
                time_slot=self.time_slot,
                date=self.date
            ).first()
            
            if existing:
                # Update existing booking
                existing.status = self.status
                existing.user = self.user
                existing.updated_at = timezone.now()
                existing.save()
                # Set this instance's pk to existing one
                self.pk = existing.pk
                return existing
        
        super().save(*args, **kwargs)
        return self
    
    def __str__(self):
        return f"{self.court} - {self.date} - {self.time_slot}"
