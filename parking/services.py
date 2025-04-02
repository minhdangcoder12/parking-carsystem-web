import cv2
import numpy as np
import easyocr
from datetime import datetime
import os
from django.conf import settings
from .models import Camera, LicensePlateLog, ParkingSession, Vehicle

class LicensePlateRecognition:
    def __init__(self):
        self.reader = easyocr.Reader(['en'])
        
    def preprocess_image(self, image):
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to remove noise while keeping edges sharp
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Edge detection
        edged = cv2.Canny(gray, 30, 200)
        
        # Find contours
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        return gray, contours
    
    def detect_license_plate(self, image):
        gray, contours = self.preprocess_image(image)
        
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * peri, True)
            
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                plate_img = gray[y:y+h, x:x+w]
                
                # OCR on the plate region
                results = self.reader.readtext(plate_img)
                
                if results:
                    text = results[0][1]
                    confidence = results[0][2]
                    
                    # Clean up the text (remove spaces and special characters)
                    text = ''.join(c for c in text if c.isalnum())
                    
                    if len(text) >= 5:  # Minimum length for a license plate
                        return text, confidence, plate_img
        
        return None, None, None
    
    def process_frame(self, camera):
        try:
            # Connect to camera stream
            cap = cv2.VideoCapture(f'rtsp://{camera.ip_address}:{camera.port}')
            
            if not cap.isOpened():
                return False
            
            ret, frame = cap.read()
            if not ret:
                return False
            
            # Detect license plate
            plate_text, confidence, plate_img = self.detect_license_plate(frame)
            
            if plate_text and confidence > 0.5:  # Confidence threshold
                # Save the plate image
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'plate_{timestamp}.jpg'
                filepath = os.path.join(settings.MEDIA_ROOT, 'license_plates', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                cv2.imwrite(filepath, plate_img)
                
                # Create log entry
                log = LicensePlateLog.objects.create(
                    camera=camera,
                    license_plate=plate_text,
                    confidence=confidence,
                    image=f'license_plates/{filename}'
                )
                
                # Process the log
                self.process_license_plate_log(log)
            
            cap.release()
            return True
            
        except Exception as e:
            print(f"Error processing camera {camera.name}: {str(e)}")
            return False
    
    def process_license_plate_log(self, log):
        if log.processed:
            return
        
        # Find the vehicle
        try:
            vehicle = Vehicle.objects.get(license_plate=log.license_plate)
            
            if log.log_type == 'check_in':
                # Create new parking session
                ParkingSession.objects.create(
                    vehicle=vehicle,
                    parking_spot=camera.parking_lot.spots.filter(status='available').first(),
                    start_time=log.timestamp
                )
            elif log.log_type == 'check_out':
                # End active parking session
                active_session = ParkingSession.objects.filter(
                    vehicle=vehicle,
                    status='active'
                ).first()
                
                if active_session:
                    active_session.end_time = log.timestamp
                    active_session.status = 'completed'
                    
                    # Calculate fee
                    duration = active_session.end_time - active_session.start_time
                    hours = duration.total_seconds() / 3600
                    active_session.fee = round(hours * 2, 2)  # $2 per hour
                    active_session.save()
            
            log.processed = True
            log.save()
            
        except Vehicle.DoesNotExist:
            print(f"Vehicle not found for license plate: {log.license_plate}") 