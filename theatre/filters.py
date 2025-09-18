import django_filters as filters

from theatre.models import Play, Performance


class PlayFilter(filters.FilterSet):
    title = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Play
        fields = ["genres", "actors", "title"]


class PerformanceFilter(filters.FilterSet):
    date_from = filters.DateFilter(
        field_name="show_time", lookup_expr="date__gte"
    )
    date_to = filters.DateFilter(
        field_name="show_time", lookup_expr="date__lte"
    )
    play = filters.NumberFilter(field_name="play_id")
    hall = filters.NumberFilter(field_name="hall_id")

    class Meta:
        model = Performance
        fields = ["date_from", "date_to", "play", "hall"]
