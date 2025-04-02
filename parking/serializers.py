from rest_framework import serializers
from .models import ParkingLot, ParkingSpot, Vehicle, ParkingSession, Reservation, ParkingAnalytics, Camera, LicensePlateLog
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class VehicleSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Vehicle
        fields = '__all__'

class ParkingSpotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSpot
        fields = '__all__'

class ParkingLotSerializer(serializers.ModelSerializer):
    spots = ParkingSpotSerializer(many=True, read_only=True)
    
    class Meta:
        model = ParkingLot
        fields = '__all__'

class ParkingSessionSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    parking_spot = ParkingSpotSerializer(read_only=True)
    
    class Meta:
        model = ParkingSession
        fields = '__all__'

class ReservationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    parking_spot = ParkingSpotSerializer(read_only=True)
    
    class Meta:
        model = Reservation
        fields = '__all__'

class ParkingAnalyticsSerializer(serializers.ModelSerializer):
    parking_lot = ParkingLotSerializer(read_only=True)
    
    class Meta:
        model = ParkingAnalytics
        fields = '__all__'

class CameraSerializer(serializers.ModelSerializer):
    parking_lot = ParkingLotSerializer(read_only=True)
    
    class Meta:
        model = Camera
        fields = '__all__'

class LicensePlateLogSerializer(serializers.ModelSerializer):
    camera = CameraSerializer(read_only=True)
    
    class Meta:
        model = LicensePlateLog
        fields = '__all__' 