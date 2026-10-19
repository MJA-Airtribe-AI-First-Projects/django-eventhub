from django.core.validators import MinValueValidator
from django.db import models


class Event(models.Model):
    # The allowed lifecycle states for an event.
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    title = models.CharField(max_length=200, blank=False, null=False)  # Event name.
    venue = models.CharField(max_length=200, blank=False, null=False)  # Where the event takes place.
    date = models.DateField(blank=False, null=False)  # Scheduled event date.
    total_seats = models.PositiveIntegerField(validators=[MinValueValidator(1)])  # Maximum venue capacity.
    available_seats = models.PositiveIntegerField()  # Seats still open for booking.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)  # Set when the record is created.

    def __str__(self):
        return f"{self.title} at {self.venue}"

    class Meta:
        # Use a clear table name and show events in date order by default.
        db_table = 'events'
        ordering = ['date']


class Reservation(models.Model):
    # Reservation states supported by the application.
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    # Deleting an event also deletes its reservations.
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reservations')
    attendee_name = models.CharField(max_length=200, blank=False, null=False)  # Name of the person booking.
    attendee_email = models.EmailField(blank=False, null=False)  # Contact email for the attendee.
    seats_reserved = models.PositiveIntegerField()  # Number of seats in this reservation.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)  # Set when the reservation is created.

    def __str__(self):
        return f"{self.attendee_name} - {self.event.title} ({self.seats_reserved} seats)"

    class Meta:
        # Show the newest reservations first.
        db_table = 'reservations'
        ordering = ['-created_at']
