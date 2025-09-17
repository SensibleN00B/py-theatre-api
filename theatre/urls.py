from django.urls import path, include
from rest_framework.routers import DefaultRouter

from theatre.views import (
    ActorViewSet,
    GenreViewSet,
    TheatreHallViewSet,
    PlayViewSet,
    PerformanceViewSet,
    ReservationViewSet,
)

router = DefaultRouter()
router.register("actors", ActorViewSet, basename="actor")
router.register("genres", GenreViewSet, basename="genre")
router.register("halls", TheatreHallViewSet, basename="hall")
router.register("plays", PlayViewSet, basename="play")
router.register("performances", PerformanceViewSet, basename="performance")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = [path("", include(router.urls))]

app_name = "theatre"
