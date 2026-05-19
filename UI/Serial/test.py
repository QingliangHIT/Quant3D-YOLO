import cv2

# Open camera, 0 for default
cap = cv2.VideoCapture(0)

# Set lower resolution and FPS
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

while True:
    # Read frame
    ret, frame = cap.read()
    if not ret:
        break

    # Video processing here
    # ...

    # Show frame
    cv2.imshow('Video', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release camera and close window
cap.release()
cv2.destroyAllWindows()
