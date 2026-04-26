# Use Roboflow API directly with requests (compatible with Python 3.14)
import requests
import base64
import os

def detect_eggs(image_path, api_key):
    # Read and encode image
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

    # API endpoint for workflow
    url = f"https://serverless.roboflow.com/{api_key}/workflows/lui-franz/general-segmentation-api"

    # Payload
    payload = {
        "images": {"image": encoded_image},
        "parameters": {"classes": "cracked-egg, normal-egg"},
        "use_cache": True
    }

    # Make request
    response = requests.post(url, json=payload)
    return response.json()

# Run detection on your data images
data_dir = "data/Eggs Classification"
api_key = "4vv6aI0WqrzKhWhFtjwP"

for category in ["Damaged", "Whole"]:  # Assuming Whole is normal
    category_path = os.path.join(data_dir, category)
    if os.path.exists(category_path):
        for img_file in os.listdir(category_path)[:5]:  # Test on first 5 images per category
            if img_file.lower().endswith(('.jpg', '.png')):
                img_path = os.path.join(category_path, img_file)
                print(f"Detecting in {img_path}...")
                result = detect_eggs(img_path, api_key)
                print(f"Result: {result}")
                print("-" * 50)