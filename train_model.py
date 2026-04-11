from huggingface_hub import hf_hub_download
from ultralytics import YOLO
import os
import shutil

# --- Configuration ---
REPO_ID = "industoai/Egg-Detection"
FILENAME = "model/egg_detector.pt"
DATA_YAML = "/Users/wii/Projects/python/egg-cv/data/eggs/data.yaml"
MODEL_SAVE_DIR = "/Users/wii/Projects/python/egg-cv/models"

os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

print("=" * 60)
print("Egg Detection Model Training Script")
print("=" * 60)

# Step 1: Download pre-trained model
print("\n[Step 1/4] Downloading pre-trained model...")
try:
    model_path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)
    print(f"Model downloaded: {model_path}")
except Exception as e:
    print(f"Error downloading model: {e}")
    exit(1)

# Step 2: Load pre-trained model
print("\n[Step 2/4] Loading pre-trained model...")
try:
    model = YOLO(model_path)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

# Step 3: Fine-tune the model
print("\n[Step 3/4] Starting training...")
print("This may take a while depending on your dataset size.")
print("-" * 40)

try:
    results = model.train(
        data=DATA_YAML,
        epochs=50,
        imgsz=640,
        batch=16,
        project=MODEL_SAVE_DIR,
        name="egg_detection_finetuned",
        exist_ok=True,
        pretrained=True,
        optimizer="SGD",
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0,
    )
    print("\nTraining completed!")
except Exception as e:
    print(f"Error during training: {e}")
    exit(1)

# Step 4: Validate the model
print("\n[Step 4/4] Validating the trained model...")
best_model_path = os.path.join(MODEL_SAVE_DIR, "egg_detection_finetuned", "weights", "best.pt")
last_model_path = os.path.join(MODEL_SAVE_DIR, "egg_detection_finetuned", "weights", "last.pt")

if os.path.exists(best_model_path):
    print(f"Best model found at: {best_model_path}")
    print("\nLoading best model for validation...")
    val_model = YOLO(best_model_path)
    val_results = val_model.val(data=DATA_YAML)
    print("\nValidation Results:")
    print(f"  mAP50: {val_results.box.map50:.4f}")
    print(f"  mAP50-95: {val_results.box.map:.4f}")
elif os.path.exists(last_model_path):
    print(f"Last model found at: {last_model_path}")
else:
    print("No trained model weights found!")

print("\n" + "=" * 60)
print("Training process finished!")
print(f"Model saved to: {MODEL_SAVE_DIR}/egg_detection_finetuned")
print("=" * 60)
