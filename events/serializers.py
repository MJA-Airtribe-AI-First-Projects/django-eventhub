from typing import override

from rest_framework import serializers

from events.models import Event, Reservation


class EventSerializer(serializers.ModelSerializer):
    reservations_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ('id', 'title', 'venue', 'date', 'total_seats', 'available_seats',
                  'status', 'created_at', 'reservations_count')

    def get_reservations_count(self, obj):
        # Count only confirmed reservations associated with this event.
        return obj.reservations.filter(status='confirmed').count()

    @override
    def validate(self, attrs):
        # For partial updates, compare supplied values with the existing values.
        total_seats = attrs.get(
            "total_seats",
            self.instance.total_seats if self.instance else None,
        )
        available_seats = attrs.get(
            "available_seats",
            self.instance.available_seats if self.instance else None,
        )

        # Capacity must be positive; zero remaining seats is allowed for sold-out events.
        if total_seats is not None and total_seats <= 0:
            raise serializers.ValidationError("Total seats must be greater than zero.")

        if (
                total_seats is not None
                and available_seats is not None
                and available_seats > total_seats
        ):
            raise serializers.ValidationError("Available seats cannot be greater than total seats.")

        return attrs


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        # Include the linked event and attendee details in reservation API data.
        fields = ['id', 'event', 'attendee_name', 'attendee_email',
                  'seats_reserved', 'status', 'created_at']
        # Status uses the model default, and created_at is set when the record is saved.
        read_only_fields = ['status', 'created_at']

    def validate_seats_reserved(self, value):
        # A reservation must request at least one seat.
        if value < 1:
            raise serializers.ValidationError("Must reserve at least 1 seat.")
        return value

    @override
    def validate(self, attrs):
        event = attrs.get('event')
        # Reservations are allowed only while an event is upcoming or ongoing.
        if event.status not in ('upcoming', 'ongoing'):
            raise serializers.ValidationError(f'Cannot reserve seats for a {event.status} event.')

        # Prevent reservations from exceeding the event's remaining capacity.
        if attrs.get('seats_reserved', 0) > event.available_seats:
            raise serializers.ValidationError(f'Only {event.available_seats} seat(s) available.')

        return attrs

    @override
    def create(self, validated_data):
        event = validated_data['event']
        # Deduct the reserved seats from the event before creating the reservation.
        event.available_seats -= validated_data['seats_reserved']
        event.save()
        return Reservation.objects.create(**validated_data)
