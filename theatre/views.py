from django.db.models import Count, F
from drf_spectacular.utils import extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

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
    PlaySerializer,
    PlayImageSerializer,
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

        if self.action == "retrieve":
            return PlayDetailSerializer

        if self.action == "upload_image":
            return PlayImageSerializer

        return PlaySerializer

    @extend_schema(
        description="Upload an image for a specific play. "
        "Accepts multipart/form-data.",
        request=PlayImageSerializer,
        responses=PlayImageSerializer,
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        parser_classes=(MultiPartParser, FormParser),
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        play = self.get_object()
        serializer = self.get_serializer(play, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


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
    """
    create:
    Create a new reservation with one or more tickets.

    list:
    Return a list of the current user's reservations.
    """

    permission_classes = [IsAuthenticated]

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
