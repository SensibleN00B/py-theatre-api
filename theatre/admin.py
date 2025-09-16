from django.contrib import admin

from theatre.models import (
    Play,
    Actor,
    Genre,
    Performance,
    Ticket,
    TheatreHall,
    Reservation,
)

admin.site.register(Play)
admin.site.register(Actor)
admin.site.register(Genre)
admin.site.register(Performance)
admin.site.register(Ticket)
admin.site.register(TheatreHall)
admin.site.register(Reservation)
