from ultralytics import YOLO
import cv2

MODEL_PATH = "models/egg_detection_finetuned/weights/best.pt"
TEST_IMAGE = "data/eggs/images/val/damaged_523.jpg"

print("Loading fine-tuned model...")
model = YOLO(MODEL_PATH)
print(f"Model classes: {model.names}")

print(f"\nTesting on image: {TEST_IMAGE}")
results = model(TEST_IMAGE, conf=0.3)

print(f"\nDetection results:")
for r in results:
    boxes = r.boxes
    if boxes is not None:
        print(f"Number of detections: {len(boxes)}")
        for i, box in enumerate(boxes):
            cls = int(box.cls)
            conf = float(box.conf)
            print(f"  Detection {i+1}: Class={model.names[cls]}, Confidence={conf:.4f}")
    else:
        print("No detections found!")

r = results[0]
im_array = r.plot()
cv2.imwrite("test_detection_output.jpg", im_array)
print("\nSaved result to test_detection_output.jpg")
