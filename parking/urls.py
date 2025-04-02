from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'parking-lots', views.ParkingLotViewSet)
router.register(r'parking-spots', views.ParkingSpotViewSet)
router.register(r'vehicles', views.VehicleViewSet, basename='vehicle')
router.register(r'parking-sessions', views.ParkingSessionViewSet, basename='parking-session')
router.register(r'reservations', views.ReservationViewSet, basename='reservation')
router.register(r'analytics', views.ParkingAnalyticsViewSet)

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Frontend URLs
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('parking-lot/<int:pk>/', views.parking_lot_detail, name='parking_lot_detail'),
    path('reserve-spot/', views.reserve_spot, name='reserve_spot'),
    path('end-session/<int:session_id>/', views.end_session, name='end_session'),
] 