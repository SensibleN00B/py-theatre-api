from django.db.models import Count, F
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from theatre.filters import PerformanceFilter, PlayFilter
from theatre.models import (
    Actor,
    Genre,
    Performance,
    Play,
    Reservation,
    TheatreHall,
)
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    PerformanceDetailSerializer,
    PerformanceListSerializer,
    PlayDetailSerializer,
    PlayImageSerializer,
    PlayListSerializer,
    PlaySerializer,
    ReservationListSerializer,
    ReservationSerializer,
    TheatreHallSerializer,
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


@extend_schema(
    tags=["Plays"],
    description=(
        "CRUD operations for plays. "
        "The list/retrieve serializers differ from the write serializer. "
        "Filtering is provided by PlayFilter. Results are ordered by title."
    ),
)
@extend_schema_view(
    list=extend_schema(
        summary="List plays",
        parameters=[
            OpenApiParameter(
                "title",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Filter by title (e.g., icontains)",
            ),
            OpenApiParameter(
                "genres",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                many=True,
                description="Filter by genre id (repeatable)",
            ),
            OpenApiParameter(
                "actors",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                many=True,
                description="Filter by actor id (repeatable)",
            ),
            OpenApiParameter(
                "min_duration",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Minimum duration in minutes",
            ),
            OpenApiParameter(
                "max_duration",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                description="Maximum duration in minutes",
            ),
        ],
    ),
)
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


@extend_schema(
    tags=["Performances"],
    description=(
        "CRUD operations for performances. List responses include seat stats: "
        "`taken` and `tickets_available`. "
        "Filtering is provided by PerformanceFilter. "
        "Results are ordered by Show time."
    ),
)
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


@extend_schema(
    tags=["Reservations"],
    description=(
        "Create a reservation with one or more tickets, "
        "and list the current user's reservations. "
        "Authentication is required. "
        "Results sorted from newest to oldest"
    ),
)
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
