from datetime import timedelta

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.core.files.uploadedfile import SimpleUploadedFile

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Ticket,
    Reservation,
)
from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    PlaySerializer,
    PlayListSerializer,
    PlayDetailSerializer,
    PlayImageSerializer,
    TheatreHallSerializer,
    PerformanceListSerializer,
    PerformanceDetailSerializer,
    TicketSerializer,
    TicketListSerializer,
    ReservationSerializer,
    ReservationListSerializer,
)


def create_sample_user(**kwargs):
    User = get_user_model()
    defaults = {"email": "user@example.com", "password": "pass12345"}
    defaults.update(kwargs)
    if kwargs.get("is_staff") or kwargs.get("is_superuser"):
        return User.objects.create_superuser(
            defaults["email"], defaults["password"]
        )
    return User.objects.create_user(defaults["email"], defaults["password"])


def create_sample_play(title="Hamlet"):
    actor1 = Actor.objects.create(first_name="John", last_name="Doe")
    actor2 = Actor.objects.create(first_name="Jane", last_name="Roe")
    genre1 = Genre.objects.create(name="Drama")
    genre2 = Genre.objects.create(name="Classic")
    play = Play.objects.create(title=title, duration=150, description="Desc")
    play.actors.set([actor1, actor2])
    play.genres.set([genre1, genre2])
    return play


def create_sample_hall(name="Main Hall", rows=5, seats_in_row=6):
    return TheatreHall.objects.create(
        name=name, rows=rows, seats_in_row=seats_in_row
    )


def create_sample_performance(play=None, hall=None, when=None):
    if play is None:
        play = create_sample_play()
    if hall is None:
        hall = create_sample_hall()
    if when is None:
        when = timezone.now() + timedelta(hours=1)
    return Performance.objects.create(
        play=play, theatre_hall=hall, show_time=when
    )


class TestSerializers(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_actor_serializer_includes_full_name(self):
        actor = Actor.objects.create(first_name="Ada", last_name="Lovelace")
        data = ActorSerializer(actor).data
        assert data["full_name"] == "Ada Lovelace"

    def test_genre_serializer(self):
        genre = Genre.objects.create(name="Comedy")
        assert GenreSerializer(genre).data == {
            "id": genre.id,
            "name": "Comedy",
        }

    def test_play_list_serializer_uses_slugs(self):
        play = create_sample_play(title="Othello")
        data = PlayListSerializer(play).data
        assert data["title"] == "Othello"
        # Actors as full_name strings
        assert all(isinstance(name, str) for name in data["actors"])
        # Genres as names
        assert all(isinstance(name, str) for name in data["genres"])

    def test_play_detail_serializer_nested(self):
        play = create_sample_play()
        data = PlayDetailSerializer(play).data
        assert isinstance(data["actors"], list) and data["actors"][0].get(
            "first_name"
        )
        assert isinstance(data["genres"], list) and data["genres"][0].get(
            "name"
        )
        assert data["image"] is None

    def test_play_image_serializer_requires_image(self):
        play = create_sample_play()
        serializer = PlayImageSerializer(play, data={})
        assert not serializer.is_valid()
        assert "image" in serializer.errors

        image = SimpleUploadedFile(
            "poster.jpg", b"filecontent", content_type="image/jpeg"
        )
        serializer = PlayImageSerializer(play, data={"image": image})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        assert instance.image

    def test_hall_serializer_has_capacity(self):
        hall = create_sample_hall(rows=10, seats_in_row=10)
        data = TheatreHallSerializer(hall).data
        assert data["hall_capacity"] == 100

    def test_performance_list_serializer_computed_fields(self):
        play = create_sample_play()
        hall = create_sample_hall(rows=3, seats_in_row=4)  # capacity 12
        perf = create_sample_performance(play=play, hall=hall)
        user = create_sample_user()
        res = Reservation.objects.create(user=user)
        Ticket.objects.create(performance=perf, reservation=res, row=1, seat=1)
        Ticket.objects.create(performance=perf, reservation=res, row=1, seat=2)

        perf_annotated = (
            Performance.objects.select_related("play", "theatre_hall")
            .annotate(
                tickets_available=F("theatre_hall__rows")
                * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
            .get(pk=perf.id)
        )

        data = PerformanceListSerializer(perf_annotated).data
        assert data["tickets_available"] == 10
        assert data["hall_capacity"] == hall.hall_capacity
        assert data["play_title"] == play.title

    def test_performance_detail_serializer_nested(self):
        perf = create_sample_performance()
        user = create_sample_user()
        res = Reservation.objects.create(user=user)
        Ticket.objects.create(performance=perf, reservation=res, row=1, seat=1)

        data = PerformanceDetailSerializer(perf).data
        assert data["play"]["title"] == perf.play.title
        assert data["theatre_hall"]["name"] == perf.theatre_hall.name
        assert data["taken_places"][0] == {"row": 1, "seat": 1}

    def test_ticket_serializer_validates_past_performance(self):
        hall = create_sample_hall(rows=3, seats_in_row=3)
        play = create_sample_play()
        perf_past = create_sample_performance(
            play=play, hall=hall, when=timezone.now() - timedelta(hours=1)
        )
        serializer = TicketSerializer(
            data={"row": 1, "seat": 1, "performance": perf_past.id}
        )
        serializer.is_valid()
        assert "performance" in serializer.errors

    def test_ticket_serializer_valid_input(self):
        hall = create_sample_hall(rows=2, seats_in_row=2)
        perf = create_sample_performance(hall=hall)
        serializer = TicketSerializer(
            data={"row": 2, "seat": 2, "performance": perf.id}
        )
        assert serializer.is_valid(), serializer.errors

    def test_reservation_serializer_create_and_duplicate_handling(self):
        user = create_sample_user()
        hall = create_sample_hall(rows=2, seats_in_row=2)
        perf = create_sample_performance(hall=hall)

        request = self.rf.post("/")
        request.user = user

        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": perf.id},
                {"row": 1, "seat": 2, "performance": perf.id},
            ]
        }
        serializer = ReservationSerializer(
            data=payload, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        assert reservation.tickets.count() == 2

        dup_payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": perf.id},
                {"row": 1, "seat": 1, "performance": perf.id},
            ]
        }
        serializer = ReservationSerializer(
            data=dup_payload, context={"request": request}
        )
        assert not serializer.is_valid()

    def test_reservation_list_serializer_nested(self):
        user = create_sample_user()
        hall = create_sample_hall(rows=2, seats_in_row=2)
        perf = create_sample_performance(hall=hall)
        res = Reservation.objects.create(user=user)
        Ticket.objects.create(performance=perf, reservation=res, row=2, seat=2)
        data = ReservationListSerializer(res).data
        assert isinstance(data["tickets"], list)
        assert (
            data["tickets"][0]["performance"]["hall_capacity"]
            == hall.hall_capacity
        )
