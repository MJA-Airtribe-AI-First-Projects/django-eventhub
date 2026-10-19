from typing import override

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from events.filters import EventFilter
from events.models import Event, Reservation
from events.serializers import EventSerializer, ReservationSerializer


class EventsModelViewSet(ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filterset_class = EventFilter

    @staticmethod
    def __validation_error(serializer: EventSerializer) -> Response:
        """Return the first serializer validation error in a generic response."""
        errors = serializer.errors
        if "non_field_errors" in errors:
            return Response({"error": str(errors["non_field_errors"][0])},
                            status=status.HTTP_400_BAD_REQUEST)

        field, messages = next(iter(errors.items()))
        return Response(
            {"error": f"{field}: {messages[0]}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def __venue_date_exists(venue, date, exclude_pk=None) -> bool:
        """Check whether another event already uses the same venue and date."""
        events = Event.objects.filter(venue=venue, date=date)
        if exclude_pk is not None:
            events = events.exclude(pk=exclude_pk)
        return events.exists()

    @override
    def create(self, request, *args, **kwargs):
        """Validate request data and create an event."""
        try:
            data = request.data

            # If capacity is omitted, start with every seat available.
            if data.get("available_seats") is None:
                data["available_seats"] = data.get("total_seats", 0)

            serializer = self.serializer_class(data=data)

            if not serializer.is_valid():
                return self.__validation_error(serializer)

            # Keep venue and date combinations unique when creating events.
            if self.__venue_date_exists(serializer.validated_data["venue"],
                                        serializer.validated_data["date"]):
                return Response(
                    {"error": "An event at this venue on this date already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_create(serializer)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @override
    def update(self, request, *args, **kwargs):
        """Update an event and adjust available seats when capacity changes."""
        try:
            instance = self.get_object()
            data = request.data.copy()

            # Adjust remaining seats by the same amount as capacity when omitted.
            if data.get("available_seats") is None:
                total_seats = data.get("total_seats", instance.total_seats)
                try:
                    total_seats = int(total_seats)
                except (TypeError, ValueError):
                    # Leave invalid capacity input for serializer validation to report.
                    total_seats = instance.total_seats
                data["available_seats"] = (
                        instance.available_seats + total_seats - instance.total_seats
                )

            serializer = self.serializer_class(instance, data=data)

            # Validate capacity constraints before saving the updated event.
            if not serializer.is_valid():
                return self.__validation_error(serializer)

            if self.__venue_date_exists(serializer.validated_data["venue"],
                                        serializer.validated_data["date"],
                                        exclude_pk=instance.pk):
                return Response(
                    {"error": "An event at this venue on this date already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_update(serializer)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReservationModelViewSet(ModelViewSet):
    """Handle reservation creation, updates, listing, and cancellation."""

    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    filterset_fields = ('event_id',)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_reservation(self, request, pk=None):
        """Cancel a reservation and return its seats to the event."""
        reservation = self.get_object()

        if reservation.status == "cancelled":
            return Response({"error": "Reservation already cancelled"}, status=status.HTTP_400_BAD_REQUEST)

        # Make the seats available again before marking the reservation cancelled.
        reservation.event.available_seats += reservation.seats_reserved
        reservation.event.save()

        reservation.status = "cancelled"
        reservation.save()

        return Response(self.get_serializer(reservation).data, status=status.HTTP_200_OK)
