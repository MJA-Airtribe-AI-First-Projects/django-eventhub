from django.urls import path, include
from rest_framework import routers

from events.views import EventsModelViewSet, ReservationModelViewSet

router = routers.DefaultRouter()
router.register(r'events', EventsModelViewSet, basename='events')
router.register(r'reservations', ReservationModelViewSet, basename='reservations')
urlpatterns = [path("", include(router.urls))]
