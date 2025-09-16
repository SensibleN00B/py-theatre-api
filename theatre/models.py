from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint

from theatre.utils import play_image_file_path

User = get_user_model()


class Actor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return self.__str__()


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Play(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    actors = models.ManyToManyField(Actor, related_name="plays")
    genres = models.ManyToManyField(Genre, related_name="plays")
    duration = models.PositiveIntegerField()
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to=play_image_file_path,
    )

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["title"]


class TheatreHall(models.Model):
    name = models.CharField(max_length=100, unique=True)
    rows = models.PositiveIntegerField()
    seats_in_row = models.PositiveIntegerField()

    @property
    def hall_capacity(self):
        return self.rows * self.seats_in_row

    def __str__(self):
        return self.name


class Performance(models.Model):
    play = models.ForeignKey(
        Play, related_name="performances", on_delete=models.PROTECT
    )
    theatre_hall = models.ForeignKey(
        TheatreHall, related_name="performances", on_delete=models.CASCADE
    )
    show_time = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=(
                    "theatre_hall",
                    "show_time",
                ),
                name="uniq_show_time_per_hall",
            )
        ]
        ordering = ["-show_time"]

    def __str__(self):
        return f"{self.play} ({self.show_time})"


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reservations"
    )

    class Meta:
        ordering = ["-created_at"]


class Ticket(models.Model):
    row = models.PositiveIntegerField()
    seat = models.PositiveIntegerField()
    performance = models.ForeignKey(
        Performance, related_name="tickets", on_delete=models.CASCADE
    )
    reservation = models.ForeignKey(
        Reservation, related_name="tickets", on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=(
                    "row",
                    "seat",
                    "performance",
                ),
                name="uniq_row_and_seat_for_performance",
            )
        ]
        ordering = ["row", "seat"]

    def __str__(self):
        return f"{self.performance} (row: {self.row}, seat: {self.seat})"

    @staticmethod
    def validate_ticket(row: int, seat: int, hall: TheatreHall) -> None:
        for value, field_name, hall_attr in [
            (row, "row", "rows"),
            (seat, "seat", "seats_in_row"),
        ]:
            max_count = getattr(hall, hall_attr)
            if not (1 <= value <= max_count):
                raise ValidationError(
                    {
                        field_name: f"{field_name.capitalize()} number must be "
                        f"between 1 and {max_count}"
                    }
                )

    def clean(self):
        self.validate_ticket(
            self.row,
            self.seat,
            self.performance.theatre_hall
        )
