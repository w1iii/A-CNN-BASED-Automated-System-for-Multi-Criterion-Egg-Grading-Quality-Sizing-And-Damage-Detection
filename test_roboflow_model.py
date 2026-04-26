import os

from roboflow import Roboflow

# Initialize Roboflow with your API key
rf = Roboflow(api_key="4vv6aI0WqrzKhWhFtjwP")  # Replace with your actual API key

# Load the model
project = rf.workspace().project(
    "boysmithv2-rohz2"
)  # Note: model_id is "boysmithv2-rohz2/1", so project is "boysmithv2-rohz2"
model = project.version(1).model

# Test images available in the project
test_images = ["egg_snapshot_2_1775580053.jpg", "test_detection_output.jpg"]

# Find the first available test image
test_image = None
for img in test_images:
    if os.path.exists(img):
        test_image = img
        break

if test_image:
    print(f"Running inference on {test_image} with model boysmithv2-rohz2/1")
    # Run inference
    result = model.predict(test_image, confidence=40, overlap=30).json()
    print("Inference result:")
    print(result)
else:
    print(
        "No test image found. Please ensure you have an image file in the project directory."
    )
