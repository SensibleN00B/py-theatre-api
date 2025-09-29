# tests/test_views.py

from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from theatre.models import (
    Actor,
    Genre,
    Performance,
    Play,
    Reservation,
    TheatreHall,
    Ticket,
)


def create_user(email="user@example.com", password="pass123"):
    return get_user_model().objects.create_user(email=email, password=password)


def create_admin(email="admin@example.com", password="pass123"):
    return get_user_model().objects.create_superuser(
        email=email, password=password
    )


def sample_play(title="Macbeth"):
    play = Play.objects.create(title=title, duration=120, description="")
    actor1 = Actor.objects.create(first_name="A", last_name="One")
    genre1 = Genre.objects.create(name=f"{title}-Drama")
    play.actors.add(actor1)
    play.genres.add(genre1)
    return play


def sample_hall(name="Blue Hall", rows=5, seats_in_row=5):
    return TheatreHall.objects.create(
        name=name, rows=rows, seats_in_row=seats_in_row
    )


def sample_performance(play=None, hall=None, when=None):
    if play is None:
        play = sample_play()
    if hall is None:
        hall = sample_hall()
    if when is None:
        when = timezone.now() + timedelta(hours=1)
    return Performance.objects.create(
        play=play, theatre_hall=hall, show_time=when
    )


def get_results(data):
    """Return list payload regardless of pagination."""
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def make_test_image(fmt="PNG", size=(2, 2), color=(1, 1, 1)):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


class PublicReadOnlyViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_can_list_resources(self):
        # Actors
        Actor.objects.create(first_name="B", last_name="B")
        Actor.objects.create(first_name="A", last_name="A")
        response = self.client.get(reverse("theatre:actor-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actors = get_results(response.data)
        self.assertGreaterEqual(len(actors), 2)
        self.assertLessEqual(actors[0]["last_name"], actors[-1]["last_name"])

        # Genres
        Genre.objects.create(name="Z")
        Genre.objects.create(name="A")
        response = self.client.get(reverse("theatre:genre-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Halls
        sample_hall(name="A")
        sample_hall(name="B")
        response = self.client.get(reverse("theatre:hall-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_cannot_write(self):
        response = self.client.post(
            reverse("theatre:actor-list"),
            {"first_name": "New", "last_name": "Actor"},
            format="json",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class AdminWriteViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin()
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_actor_genre_hall_play(self):
        # Actor
        actor_response = self.client.post(
            reverse("theatre:actor-list"),
            {"first_name": "New", "last_name": "Star"},
            format="json",
        )
        self.assertEqual(actor_response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", actor_response.data)
        actor_id = actor_response.data["id"]

        # Genre
        genre_response = self.client.post(
            reverse("theatre:genre-list"),
            {"name": "Thriller"},
            format="json",
        )
        self.assertEqual(genre_response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", genre_response.data)
        genre_id = genre_response.data["id"]

        # Hall
        hall_response = self.client.post(
            reverse("theatre:hall-list"),
            {"name": "Grand", "rows": 10, "seats_in_row": 12},
            format="json",
        )
        self.assertEqual(hall_response.status_code, status.HTTP_201_CREATED)

        # Play
        payload = {
            "title": "Cast Away",
            "duration": 143,
            "description": "Survival drama at sea",
            "actors": [actor_id],
            "genres": [genre_id],
        }
        play_response = self.client.post(
            reverse("theatre:play-list"),
            payload,
            format="json",
        )
        self.assertEqual(play_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(play_response.data.get("title"), "Cast Away")

    def test_play_upload_image_action(self):
        play = sample_play(title="PosterTest")
        url = reverse("theatre:play-upload-image", args=[play.id])
        image_bytes = make_test_image(fmt="JPEG")
        image_file = SimpleUploadedFile(
            "poster.jpg", image_bytes, content_type="image/jpeg"
        )
        response = self.client.post(
            url, {"image": image_file}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        play.refresh_from_db()
        self.assertTrue(bool(play.image))


class PlayAndPerformanceReadTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_play_list_and_retrieve_serializers(self):
        play = sample_play(title="Lear")

        # List
        response = self.client.get(reverse("theatre:play-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plays = get_results(response.data)
        self.assertGreaterEqual(len(plays), 1)
        self.assertIn("actors", plays[0])

        # Retrieve
        response = self.client.get(
            reverse("theatre:play-detail", args=[play.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("description", response.data)
        self.assertIsInstance(response.data["actors"], list)

    def test_performance_list_annotations_and_detail(self):
        hall = sample_hall(rows=3, seats_in_row=3)  # cap 9
        performance = sample_performance(hall=hall)
        user = create_user()
        reservation1 = Reservation.objects.create(user=user)
        Ticket.objects.create(
            performance=performance, reservation=reservation1, row=1, seat=1
        )
        Ticket.objects.create(
            performance=performance, reservation=reservation1, row=1, seat=2
        )
        Ticket.objects.create(
            performance=performance, reservation=reservation1, row=1, seat=3
        )

        response = self.client.get(reverse("theatre:performance-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        performances = get_results(response.data)
        self.assertGreaterEqual(len(performances), 1)
        self.assertEqual(performances[0]["tickets_available"], 6)

        response = self.client.get(
            reverse("theatre:performance-detail", args=[performance.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("taken_places", response.data)


class ReservationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        anonymous_client = APIClient()
        response = anonymous_client.get(reverse("theatre:reservation-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_user_reservations(self):
        hall = sample_hall()
        performance = sample_performance(hall=hall)
        other_user = create_user(email="other@example.com")
        other_reservation = Reservation.objects.create(user=other_user)
        Ticket.objects.create(
            performance=performance,
            reservation=other_reservation,
            row=1,
            seat=1,
        )
        my_reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            performance=performance, reservation=my_reservation, row=1, seat=2
        )

        response = self.client.get(reverse("theatre:reservation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = get_results(response.data)
        self.assertEqual(len(items), 1)

    def test_create_reservation_success(self):
        hall = sample_hall(rows=2, seats_in_row=2)
        performance = sample_performance(hall=hall)
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": performance.id},
                {"row": 2, "seat": 2, "performance": performance.id},
            ]
        }
        response = self.client.post(
            reverse("theatre:reservation-list"), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

    def test_create_reservation_rejects_past_performance(self):
        hall = sample_hall(rows=2, seats_in_row=2)
        past_performance = sample_performance(
            hall=hall, when=timezone.now() - timedelta(hours=1)
        )
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "performance": past_performance.id}
            ]
        }
        response = self.client.post(
            reverse("theatre:reservation-list"), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("performance", str(response.data))

    def test_create_reservation_duplicate_seat_error(self):
        hall = sample_hall(rows=2, seats_in_row=2)
        performance = sample_performance(hall=hall)
        first_reservation = Reservation.objects.create(user=self.user)
        Ticket.objects.create(
            performance=performance,
            reservation=first_reservation,
            row=1,
            seat=1,
        )

        payload = {
            "tickets": [{"row": 1, "seat": 1, "performance": performance.id}]
        }
        response = self.client.post(
            reverse("theatre:reservation-list"), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unique", str(response.data).lower())
