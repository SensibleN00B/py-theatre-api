from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient
from rest_framework import status

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Ticket,
    Reservation,
)


def create_user(email="user@example.com", password="pass123"):
    return get_user_model().objects.create_user(email=email, password=password)


def create_admin(email="admin@example.com", password="pass123"):
    return get_user_model().objects.create_superuser(email=email, password=password)


def sample_play(title="Macbeth"):
    play = Play.objects.create(title=title, duration=120, description="")
    a1 = Actor.objects.create(first_name="A", last_name="One")
    g1 = Genre.objects.create(name=f"{title}-Drama")
    play.actors.add(a1)
    play.genres.add(g1)
    return play


def sample_hall(name="Blue Hall", rows=5, seats_in_row=5):
    return TheatreHall.objects.create(name=name, rows=rows, seats_in_row=seats_in_row)


def sample_performance(play=None, hall=None, when=None):
    if play is None:
        play = sample_play()
    if hall is None:
        hall = sample_hall()
    if when is None:
        when = timezone.now() + timedelta(hours=1)
    return Performance.objects.create(play=play, theatre_hall=hall, show_time=when)


class PublicReadOnlyViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_can_list_resources(self):
        # Actors
        Actor.objects.create(first_name="B", last_name="B")
        Actor.objects.create(first_name="A", last_name="A")
        url = "/api/theatre/actors/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Ordered by last_name, first_name
        self.assertLessEqual(res.data[0]["last_name"], res.data[-1]["last_name"])

        # Genres
        Genre.objects.create(name="Z")
        Genre.objects.create(name="A")
        res = self.client.get("/api/theatre/genres/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Halls
        sample_hall(name="A")
        sample_hall(name="B")
        res = self.client.get("/api/theatre/halls/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_public_cannot_write(self):
        res = self.client.post(
            "/api/theatre/actors/",
            {"first_name": "New", "last_name": "Actor"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminWriteViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin()
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_actor_genre_hall_play(self):
        res = self.client.post(
            "/api/theatre/actors/", {"first_name": "New", "last_name": "Star"}
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(
            "/api/theatre/genres/", {"name": "Thriller"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(
            "/api/theatre/halls/",
            {"name": "Grand", "rows": 10, "seats_in_row": 12},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Create a play with relations
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        genre = Genre.objects.create(name="Drama2")
        payload = {
            "title": "Cast Away",
            "duration": 143,
            "description": "",
            "actors": [actor.id],
            "genres": [genre.id],
        }
        res = self.client.post("/api/theatre/plays/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_play_upload_image_action(self):
        play = sample_play(title="PosterTest")
        url = f"/api/theatre/plays/{play.id}/upload-image/"
        image = SimpleUploadedFile("poster.jpg", b"img", content_type="image/jpeg")
        res = self.client.post(url, {"image": image}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        play.refresh_from_db()
        self.assertTrue(bool(play.image))


class PlayAndPerformanceReadTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_play_list_and_retrieve_serializers(self):
        play = sample_play(title="Lear")
        # List
        res = self.client.get("/api/theatre/plays/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("actors", res.data[0])  # slugs in list serializer
        # Retrieve
        res = self.client.get(f"/api/theatre/plays/{play.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("description", res.data)
        self.assertIsInstance(res.data["actors"], list)

    def test_performance_list_annotations_and_detail(self):
        hall = sample_hall(rows=3, seats_in_row=3)  # cap 9
        perf = sample_performance(hall=hall)
        # Book 3 tickets
        user = create_user()
        resv = Reservation.objects.create(user=user)
        Ticket.objects.create(performance=perf, reservation=resv, row=1, seat=1)
        Ticket.objects.create(performance=perf, reservation=resv, row=1, seat=2)
        Ticket.objects.create(performance=perf, reservation=resv, row=1, seat=3)

        res = self.client.get("/api/theatre/performances/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["tickets_available"], 6)

        res = self.client.get(f"/api/theatre/performances/{perf.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("taken_places", res.data)


class ReservationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        client = APIClient()
        res = client.get("/api/theatre/reservations/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_user_reservations(self):
        hall = sample_hall()
        perf = sample_performance(hall=hall)
        # Create reservation for another user
        other = create_user(email="other@example.com")
        other_res = Reservation.objects.create(user=other)
        Ticket.objects.create(performance=perf, reservation=other_res, row=1, seat=1)

        # Create reservation for current user
        my_res = Reservation.objects.create(user=self.user)
        Ticket.objects.create(performance=perf, reservation=my_res, row=1, seat=2)

        res = self.client.get("/api/theatre/reservations/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Only 1 reservation for current user
        self.assertEqual(len(res.data), 1)

    def test_create_reservation_success(self):
        hall = sample_hall(rows=2, seats_in_row=2)
        perf = sample_performance(hall=hall)
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": perf.id},
                {"row": 2, "seat": 2, "performance": perf.id},
            ]
        }
        res = self.client.post("/api/theatre/reservations/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", res.data)

    def test_create_reservation_rejects_past_performance(self):
        hall = sample_hall(rows=2, seats_in_row=2)
        past_perf = sample_performance(hall=hall, when=timezone.now() - timedelta(hours=1))
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": past_perf.id},
            ]
        }
        res = self.client.post("/api/theatre/reservations/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("performance", str(res.data))

    def test_create_reservation_duplicate_seat_error(self):
        hall = sample_hall(rows=2, seats_in_row=2)
        perf = sample_performance(hall=hall)
        # First, take a seat so second reservation conflicts
        first_res = Reservation.objects.create(user=self.user)
        Ticket.objects.create(performance=perf, reservation=first_res, row=1, seat=1)

        payload = {"tickets": [{"row": 1, "seat": 1, "performance": perf.id}]}
        res = self.client.post("/api/theatre/reservations/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Some seat is already taken", str(res.data))
