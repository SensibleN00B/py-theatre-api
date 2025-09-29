from rest_framework.routers import DefaultRouter

from theatre.views import (
    ActorViewSet,
    GenreViewSet,
    PerformanceViewSet,
    PlayViewSet,
    ReservationViewSet,
    TheatreHallViewSet,
)

router = DefaultRouter()
router.register("actors", ActorViewSet, basename="actor")
router.register("genres", GenreViewSet, basename="genre")
router.register("halls", TheatreHallViewSet, basename="hall")
router.register("plays", PlayViewSet, basename="play")
router.register("performances", PerformanceViewSet, basename="performance")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = router.urls

app_name = "theatre"
