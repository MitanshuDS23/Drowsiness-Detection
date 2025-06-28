import cv2
import numpy as np
import pygame
import time

# Initialize the camera
cap = cv2.VideoCapture(0)

# Check if camera opened successfully
if not cap.isOpened():
    print("Error: Cannot open camera")
    exit()

# Set camera properties
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Load OpenCV's face and eye detectors
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Status marking for the current state
sleep = 0
drowsy = 0
active = 0
status = ""
color = (0, 0, 0)

# Load the warning sound file using pygame
pygame.mixer.init()
try:
    warning_sound = pygame.mixer.Sound("warning_sound.wav")
except pygame.error:
    print("Warning: Could not load warning_sound.wav - continuing without audio")
    warning_sound = None

# Eye aspect ratio calculation
def calculate_ear(eye_points):
    """Calculate Eye Aspect Ratio for blink detection"""
    if len(eye_points) < 6:
        return 0.3  # Default value when not enough points
    
    # Vertical eye landmarks
    A = np.linalg.norm(eye_points[1] - eye_points[5])
    B = np.linalg.norm(eye_points[2] - eye_points[4])
    
    # Horizontal eye landmark
    C = np.linalg.norm(eye_points[0] - eye_points[3])
    
    # Eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear

def detect_blink_from_eyes(eyes, gray_roi):
    """Detect blink based on eye regions"""
    if len(eyes) < 2:
        return 1  # Default to partially open if can't detect both eyes
    
    total_ear = 0
    eye_count = 0
    
    for (ex, ey, ew, eh) in eyes:
        eye_roi = gray_roi[ey:ey+eh, ex:ex+ew]
        
        # Simple blink detection based on eye region intensity
        mean_intensity = np.mean(eye_roi)
        
        # Normalize and calculate EAR-like metric
        if mean_intensity < 50:  # Dark region (closed eye)
            ear = 0.15
        elif mean_intensity < 100:  # Partially open
            ear = 0.23
        else:  # Open eye
            ear = 0.3
            
        total_ear += ear
        eye_count += 1
    
    if eye_count == 0:
        return 1
    
    avg_ear = total_ear / eye_count
    
    # Return blink status
    if avg_ear < 0.2:
        return 0  # Closed/sleeping
    elif avg_ear < 0.25:
        return 1  # Drowsy
    else:
        return 2  # Active

face_frame = None

# Initialize timer variables
start_time = time.time()
current_time = 0

# Define the message coordinates
message_x = 10
message_y = 70
message = ""

print("Starting OpenCV-based drowsiness detection...")
print("Press ESC to exit")

frame_count = 0

while True:
    ret, frame = cap.read()
    
    # Check if frame was read successfully
    if not ret or frame is None:
        print("Error: Failed to read frame from camera")
        break
    
    frame_count += 1
    
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    # Calculate current time
    current_time = int(time.time() - start_time)
    timer_text = f"{current_time//60:02d}:{current_time%60:02d}"
    
    # Initialize face_frame
    face_frame = frame.copy()
    
    if len(faces) == 0:
        # No face detected
        status = "No face detected"
        color = (0, 255, 255)  # Yellow
    
    for (x, y, w, h) in faces:
        # Draw rectangle around face
        cv2.rectangle(face_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Region of interest for eyes
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = face_frame[y:y+h, x:x+w]
        
        # Detect eyes within the face region
        eyes = eye_cascade.detectMultiScale(roi_gray)
        
        # Draw rectangles around eyes
        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
        
        # Detect blink status
        blink_status = detect_blink_from_eyes(eyes, roi_gray)
        
        # Update drowsiness state
        if blink_status == 0:  # Eyes closed
            sleep += 1
            drowsy = 0
            active = 0
            if sleep > 6:
                status = "SLEEPING !!!"
                color = (255, 0, 0)  # Red
                if warning_sound:
                    warning_sound.play()
        elif blink_status == 1:  # Drowsy
            sleep = 0
            active = 0
            drowsy += 1
            if drowsy > 6:
                status = "Drowsy !"
                color = (0, 0, 255)  # Blue
        else:  # Active
            drowsy = 0
            sleep = 0
            active += 1
            if active > 6:
                status = "Active :)"
                color = (0, 255, 0)  # Green
        
        # Check for break reminder
        if current_time >= 10 and current_time <= 15:
            message = "You have been driving for 10 seconds. You should take a break!"
        elif current_time > 15:
            message = ""
    
    # Display the status text and timer
    cv2.putText(frame, status, (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
    cv2.putText(frame, "Time: " + timer_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    # Display break message if needed
    if message:
        cv2.putText(frame, message, (message_x, message_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    # Display number of detected faces and eyes
    cv2.putText(frame, f"Faces: {len(faces)}", (10, frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Display the frames
    cv2.imshow("Frame", frame)
    cv2.imshow("Result of detector", face_frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC key
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()
print("Drowsiness detection stopped")