from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ParkingLot(models.Model):
    name = models.CharField(max_length=100)
    total_spots = models.IntegerField()
    available_spots = models.IntegerField()
    location = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ParkingSpot(models.Model):
    SPOT_STATUS = (
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Maintenance'),
    )
    
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='spots')
    spot_number = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=SPOT_STATUS, default='available')
    is_handicap = models.BooleanField(default=False)
    is_ev_charging = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.parking_lot.name} - Spot {self.spot_number}"

class Vehicle(models.Model):
    VEHICLE_TYPES = (
        ('car', 'Car'),
        ('motorcycle', 'Motorcycle'),
        ('truck', 'Truck'),
        ('bus', 'Bus'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    license_plate = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    color = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.license_plate} - {self.vehicle_type}"

class ParkingSession(models.Model):
    SESSION_STATUS = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='active')
    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.parking_spot.spot_number}"

class Reservation(models.Model):
    RESERVATION_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=RESERVATION_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.vehicle.license_plate}"

class ParkingAnalytics(models.Model):
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE)
    date = models.DateField()
    total_vehicles = models.IntegerField()
    peak_hour_occupancy = models.IntegerField()
    average_occupancy = models.FloatField()
    revenue = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parking_lot.name} - {self.date}"

class Camera(models.Model):
    CAMERA_STATUS = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    )
    
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(default=8000)
    status = models.CharField(max_length=20, choices=CAMERA_STATUS, default='inactive')
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='cameras')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.parking_lot.name}"

class LicensePlateLog(models.Model):
    LOG_TYPE = (
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
    )
    
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    license_plate = models.CharField(max_length=20)
    log_type = models.CharField(max_length=20, choices=LOG_TYPE)
    confidence = models.FloatField()
    image = models.ImageField(upload_to='license_plates/')
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.license_plate} - {self.log_type} - {self.timestamp}"
