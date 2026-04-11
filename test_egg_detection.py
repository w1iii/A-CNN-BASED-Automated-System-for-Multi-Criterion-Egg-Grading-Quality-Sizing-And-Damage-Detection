import os
import sys

from huggingface_hub import hf_hub_download
from ultralytics import YOLO

# --- Prerequisites ---
# Ensure you have installed the necessary libraries:
# pip install huggingface_hub ultralytics opencv-python
# --- Configuration ---
REPO_ID = "industoai/Egg-Detection"
FILENAME = "model/egg_detector.pt"
MODEL_DIR = "models"  # Directory to store downloaded models
os.makedirs(MODEL_DIR, exist_ok=True)  # Create model directory if it doesn't exist
# --- Video Source Configuration ---
# Set VIDEO_SOURCE to:
# - 0 for the default webcam.
# - A path to a video file (e.g., "/path/to/your/video.mp4").
# - None to skip video processing and only download the model.
VIDEO_SOURCE = (
    1  # Example: Use default webcam. Change to a video file path or None as needed.
)
# --- Output Directory ---
# Directory where results (like saved frames or videos) will be stored.
SAVE_DIR = "runs/detect/egg_live_view"
os.makedirs(SAVE_DIR, exist_ok=True)
# --- Model Loading ---
model_path = None
try:
    print(f"Attempting to download model from Hugging Face: {REPO_ID}/{FILENAME}")
    # hf_hub_download handles caching, so it won't re-download if already present
    model_path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)
    print(f"Model successfully downloaded or found at: {model_path}")
    print("Loading YOLO model...")
    model = YOLO(model_path)
    print("YOLO model loaded successfully.")
    # --- Inference on Video Source ---
    if VIDEO_SOURCE is not None:
        if isinstance(VIDEO_SOURCE, int):
            print(
                f"Starting live view from webcam (source: {VIDEO_SOURCE}). Press 'q' to quit in the display window."
            )
        elif isinstance(VIDEO_SOURCE, str):
            if os.path.exists(VIDEO_SOURCE):
                print(
                    f"Starting live view from video file: {VIDEO_SOURCE}. Press 'q' to quit in the display window."
                )
            else:
                print(
                    f"Error: The specified video file was not found at '{VIDEO_SOURCE}'."
                )
                print("Please ensure the path is correct and the video file exists.")
                sys.exit(1)
        else:
            print(
                f"Error: Invalid VIDEO_SOURCE '{VIDEO_SOURCE}'. Please provide a webcam index (int) or a valid video file path (str)."
            )
            sys.exit(1)
        # When show=True, the model() call directly handles opening a window and displaying frames.
        # It will block execution until the stream is finished or the user quits (by pressing 'q').
        # We remove 'stream=True' here as 'show=True' implies processing and displaying frames.
        print(
            f"Processing video stream from: {VIDEO_SOURCE}. Results will be saved to '{SAVE_DIR}'. Press 'q' in the display window to quit."
        )

        # The model() call with source and show=True will block until the stream ends or is quit.
        results = model(source=VIDEO_SOURCE, show=True, save_dir=SAVE_DIR)
        # This print statement will only be reached after the display window is closed or the stream ends.
        print("Live view processing finished or window closed.")
    else:
        print("VIDEO_SOURCE is set to None. Skipping video processing.")
except ImportError as e:
    print(f"Error: A required library is not installed. {e}")
    print(
        "Please install the necessary libraries: pip install huggingface_hub ultralytics opencv-python"
    )
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)
