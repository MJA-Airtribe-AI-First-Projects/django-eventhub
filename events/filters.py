from django_filters import FilterSet, filters

from events.models import Event


class EventFilter(FilterSet):
    status = filters.CharFilter(field_name='status', lookup_expr='exact')
    venue = filters.CharFilter(field_name='venue', lookup_expr='icontains')

    class Meta:
        model = Event
        fields = ('status', 'venue')
