import os

from ultralytics import YOLO

MODEL_PATH = (
    "/Users/wii/Projects/python/egg-cv/models/egg_detection_finetuned/weights/best.pt"
)
VIDEO_SOURCE = 1

if not os.path.exists(MODEL_PATH):
    print(f"Error: Trained model not found at {MODEL_PATH}")
    print("Please run 'python3 train_model.py' first to train the model.")
    exit(1)

print("Loading fine-tuned model...")
model = YOLO(MODEL_PATH)
print("Model loaded successfully!")

print(f"\nClasses: {model.names}")
print(f"Starting live view from webcam (source: {VIDEO_SOURCE})")
print("Press 'q' in the display window to quit.\n")

results = model(source=VIDEO_SOURCE, show=True)
print("Live view closed.")
