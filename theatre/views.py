from django.db.models import Count, F
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from theatre.filters import PlayFilter, PerformanceFilter
from theatre.models import (
    Actor,
    Genre,
    TheatreHall,
    Play,
    Performance,
    Reservation,
)
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    TheatreHallSerializer,
    PlayListSerializer,
    PlayDetailSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    ReservationSerializer,
    ReservationListSerializer,
)


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.order_by("last_name", "first_name")
    serializer_class = ActorSerializer


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.order_by("name")
    serializer_class = GenreSerializer


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.order_by("name")
    serializer_class = TheatreHallSerializer


class PlayViewSet(viewsets.ModelViewSet):
    filterset_class = PlayFilter

    def get_queryset(self):
        return Play.objects.prefetch_related("actors", "genres").order_by(
            "title"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer
        return PlayDetailSerializer


class PerformanceViewSet(viewsets.ModelViewSet):
    filterset_class = PerformanceFilter

    def get_queryset(self):
        return (
            Performance.objects.select_related("play", "theatre_hall")
            .annotate(
                taken=Count("tickets"),
                tickets_available=F("theatre_hall__rows")
                * F("theatre_hall__seats_in_row")
                - Count("tickets"),
            )
            .order_by("show_time")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer
        return PerformanceDetailSerializer


class ReservationViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        return (
            Reservation.objects.filter(user=self.request.user)
            .prefetch_related(
                "tickets__performance__theatre_hall",
                "tickets__performance__play",
            )
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationSerializer
        return ReservationListSerializer
