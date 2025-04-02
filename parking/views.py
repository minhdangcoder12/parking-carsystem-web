from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ParkingLot, ParkingSpot, Vehicle, ParkingSession, Reservation, ParkingAnalytics
from .serializers import (
    ParkingLotSerializer, ParkingSpotSerializer, VehicleSerializer,
    ParkingSessionSerializer, ReservationSerializer, ParkingAnalyticsSerializer
)
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import numpy as np
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import timedelta
import json

# Create your views here.

class ParkingLotViewSet(viewsets.ModelViewSet):
    queryset = ParkingLot.objects.all()
    serializer_class = ParkingLotSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        parking_lot = self.get_object()
        return Response({
            'total_spots': parking_lot.total_spots,
            'available_spots': parking_lot.available_spots,
            'occupancy_rate': (parking_lot.total_spots - parking_lot.available_spots) / parking_lot.total_spots * 100
        })

    @action(detail=True, methods=['get'])
    def predict_occupancy(self, request, pk=None):
        parking_lot = self.get_object()
        # Get historical data
        historical_data = ParkingAnalytics.objects.filter(parking_lot=parking_lot)
        
        if not historical_data.exists():
            return Response({'error': 'Not enough historical data for prediction'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare data for prediction
        df = pd.DataFrame(list(historical_data.values()))
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        
        # Train model
        X = df[['day_of_week', 'month']]
        y = df['average_occupancy']
        
        model = RandomForestRegressor(n_estimators=100)
        model.fit(X, y)
        
        # Predict for next day
        next_day = timezone.now().date() + timezone.timedelta(days=1)
        prediction_data = np.array([[next_day.weekday(), next_day.month]])
        predicted_occupancy = model.predict(prediction_data)[0]
        
        return Response({
            'date': next_day,
            'predicted_occupancy': predicted_occupancy
        })

class ParkingSpotViewSet(viewsets.ModelViewSet):
    queryset = ParkingSpot.objects.all()
    serializer_class = ParkingSpotSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def available_spots(self, request):
        spots = self.get_queryset().filter(status='available')
        serializer = self.get_serializer(spots, many=True)
        return Response(serializer.data)

class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Vehicle.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ParkingSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ParkingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ParkingSession.objects.filter(vehicle__user=self.request.user)

    def perform_create(self, serializer):
        vehicle = get_object_or_404(Vehicle, id=self.request.data['vehicle_id'], user=self.request.user)
        spot = get_object_or_404(ParkingSpot, id=self.request.data['spot_id'])
        serializer.save(vehicle=vehicle, parking_spot=spot, start_time=timezone.now())

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        session = self.get_object()
        session.end_time = timezone.now()
        session.status = 'completed'
        session.save()
        
        # Calculate fee (example: $2 per hour)
        duration = session.end_time - session.start_time
        hours = duration.total_seconds() / 3600
        session.fee = round(hours * 2, 2)
        session.save()
        
        # Update parking spot status
        session.parking_spot.status = 'available'
        session.parking_spot.save()
        
        return Response(self.get_serializer(session).data)

class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        vehicle = get_object_or_404(Vehicle, id=self.request.data['vehicle_id'], user=self.request.user)
        spot = get_object_or_404(ParkingSpot, id=self.request.data['spot_id'])
        serializer.save(user=self.request.user, vehicle=vehicle, parking_spot=spot)

class ParkingAnalyticsViewSet(viewsets.ModelViewSet):
    queryset = ParkingAnalytics.objects.all()
    serializer_class = ParkingAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def daily_stats(self, request):
        today = timezone.now().date()
        stats = self.get_queryset().filter(date=today)
        serializer = self.get_serializer(stats, many=True)
        return Response(serializer.data)

def home(request):
    parking_lots = ParkingLot.objects.all()
    return render(request, 'home.html', {'parking_lots': parking_lots})

@login_required
def dashboard(request):
    # Get user's active sessions
    active_sessions = ParkingSession.objects.filter(
        vehicle__user=request.user,
        status='active'
    )
    
    # Get user's upcoming reservations
    upcoming_reservations = Reservation.objects.filter(
        user=request.user,
        start_time__gte=timezone.now(),
        status='confirmed'
    ).order_by('start_time')[:5]
    
    # Get user's vehicles
    vehicles = Vehicle.objects.filter(user=request.user)
    
    # Calculate total spent
    total_spent = ParkingSession.objects.filter(
        vehicle__user=request.user,
        status='completed'
    ).aggregate(total=models.Sum('fee'))['total'] or 0
    
    # Get recent sessions
    recent_sessions = ParkingSession.objects.filter(
        vehicle__user=request.user
    ).order_by('-start_time')[:5]
    
    # Prepare chart data
    last_7_days = [timezone.now().date() - timedelta(days=i) for i in range(6, -1, -1)]
    chart_data = []
    chart_labels = []
    
    for date in last_7_days:
        analytics = ParkingAnalytics.objects.filter(
            parking_lot__in=ParkingLot.objects.all(),
            date=date
        ).aggregate(avg_occupancy=models.Avg('average_occupancy'))
        
        chart_data.append(float(analytics['avg_occupancy'] or 0))
        chart_labels.append(date.strftime('%Y-%m-%d'))
    
    context = {
        'active_sessions_count': active_sessions.count(),
        'upcoming_reservations_count': upcoming_reservations.count(),
        'vehicles_count': vehicles.count(),
        'total_spent': total_spent,
        'recent_sessions': recent_sessions,
        'upcoming_reservations': upcoming_reservations,
        'chart_data': json.dumps(chart_data),
        'chart_labels': json.dumps(chart_labels),
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def parking_lot_detail(request, pk):
    parking_lot = get_object_or_404(ParkingLot, pk=pk)
    spots = parking_lot.spots.all()
    
    # Get AI prediction for next day
    historical_data = ParkingAnalytics.objects.filter(parking_lot=parking_lot)
    prediction = None
    
    if historical_data.exists():
        df = pd.DataFrame(list(historical_data.values()))
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        
        X = df[['day_of_week', 'month']]
        y = df['average_occupancy']
        
        model = RandomForestRegressor(n_estimators=100)
        model.fit(X, y)
        
        next_day = timezone.now().date() + timedelta(days=1)
        prediction_data = np.array([[next_day.weekday(), next_day.month]])
        prediction = model.predict(prediction_data)[0]
    
    context = {
        'parking_lot': parking_lot,
        'spots': spots,
        'prediction': prediction
    }
    
    return render(request, 'parking_lot_detail.html', context)

@login_required
def reserve_spot(request):
    if request.method == 'POST':
        spot_id = request.POST.get('spot_id')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        vehicle_id = request.POST.get('vehicle_id')
        
        spot = get_object_or_404(ParkingSpot, id=spot_id)
        vehicle = get_object_or_404(Vehicle, id=vehicle_id, user=request.user)
        
        # Check if spot is available for the requested time
        conflicting_reservations = Reservation.objects.filter(
            parking_spot=spot,
            status='confirmed',
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if conflicting_reservations.exists():
            messages.error(request, 'This spot is not available for the selected time period.')
            return redirect('reserve_spot')
        
        reservation = Reservation.objects.create(
            user=request.user,
            vehicle=vehicle,
            parking_spot=spot,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        
        messages.success(request, 'Reservation request submitted successfully.')
        return redirect('dashboard')
    
    available_spots = ParkingSpot.objects.filter(status='available')
    vehicles = Vehicle.objects.filter(user=request.user)
    
    context = {
        'available_spots': available_spots,
        'vehicles': vehicles
    }
    
    return render(request, 'reserve_spot.html', context)

@login_required
def end_session(request, session_id):
    session = get_object_or_404(ParkingSession, id=session_id, vehicle__user=request.user)
    
    if session.status == 'active':
        session.end_time = timezone.now()
        session.status = 'completed'
        
        # Calculate fee (example: $2 per hour)
        duration = session.end_time - session.start_time
        hours = duration.total_seconds() / 3600
        session.fee = round(hours * 2, 2)
        session.save()
        
        # Update parking spot status
        session.parking_spot.status = 'available'
        session.parking_spot.save()
        
        messages.success(request, f'Parking session ended. Fee: ${session.fee}')
    else:
        messages.error(request, 'This session has already ended.')
    
    return redirect('dashboard')
