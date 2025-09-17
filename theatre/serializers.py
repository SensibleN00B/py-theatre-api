from django.db import transaction, IntegrityError
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Ticket,
    Reservation,
)


class ActorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="full_name", read_only=True)

    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class PlaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "duration",
            "description",
            "actors",
            "genres",
        )


class PlayListSerializer(PlaySerializer):
    actors = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name",
    )
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )

    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "duration",
            "actors",
            "genres",
        )


class PlayDetailSerializer(serializers.ModelSerializer):
    actors = ActorSerializer(many=True, read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Play
        fields = (
            "id",
            "title",
            "duration",
            "description",
            "actors",
            "genres",
            "image",
        )


class TheatreHallSerializer(serializers.ModelSerializer):
    hall_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = TheatreHall
        fields = (
            "id",
            "name",
            "rows",
            "seats_in_row",
            "hall_capacity",
        )


class PerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performance
        fields = ("id", "play", "theatre_hall", "show_time")


class PerformanceListSerializer(PerformanceSerializer):
    play_title = serializers.CharField(source="play.title", read_only=True)
    play_image = serializers.ImageField(source="play.image", read_only=True)
    hall_name = serializers.CharField(
        source="theatre_hall.name", read_only=True
    )
    hall_capacity = serializers.IntegerField(
        source="theatre_hall.hall_capacity", read_only=True
    )
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Performance
        fields = (
            "id",
            "show_time",
            "play_title",
            "play_image",
            "hall_name",
            "hall_capacity",
            "tickets_available",
        )


class TicketSeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat")


class PerformanceDetailSerializer(serializers.ModelSerializer):
    play = PlayListSerializer(read_only=True)
    theatre_hall = TheatreHallSerializer(read_only=True)
    taken_places = TicketSeatSerializer(
        source="tickets",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Performance
        fields = (
            "id",
            "show_time",
            "play",
            "theatre_hall",
            "taken_places",
        )


class TicketSerializer(serializers.ModelSerializer):
    performance = serializers.PrimaryKeyRelatedField(
        queryset=Performance.objects.select_related("theatre_hall")
    )

    class Meta:
        model = Ticket
        fields = (
            "id",
            "row",
            "seat",
            "performance",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        data = super().validate(attrs=attrs)
        performance = attrs["performance"]
        if performance.show_time < timezone.now():
            raise ValidationError(
                {"performance": "Performance is in the past."}
            )
        Ticket.validate_ticket(
            row=attrs["row"],
            seat=attrs["seat"],
            hall=performance.theatre_hall,
        )
        return data


class TicketListSerializer(TicketSerializer):
    performance = PerformanceListSerializer(read_only=True)


class ReservationSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, allow_empty=False, write_only=True)

    class Meta:
        model = Reservation
        fields = (
            "id",
            "tickets",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        user = self.context["request"].user
        items = validated_data.pop("tickets")
        with transaction.atomic():
            reservation = Reservation.objects.create(user=user)
            tickets = [
                Ticket(reservation=reservation, **item) for item in items
            ]
            try:
                Ticket.objects.bulk_create(tickets)
            except IntegrityError:
                raise ValidationError(
                    {
                        "detail": "Some seat is already taken for this performance."
                    }
                )
        return reservation


class ReservationListSerializer(ReservationSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
