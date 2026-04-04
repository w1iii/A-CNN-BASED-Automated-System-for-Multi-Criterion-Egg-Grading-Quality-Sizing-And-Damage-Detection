"""
Convert existing egg classification dataset to YOLO detection format.
Uses edge detection to find egg boundaries and generate bounding boxes.
"""
import os
import cv2
import numpy as np
import yaml
from pathlib import Path

DAMAGED_DIR = "data/Eggs Classification/Damaged"
NOT_DAMAGED_DIR = "data/Eggs Classification/Not Damaged"
OUTPUT_BASE = "data/eggs"

def find_egg_contour(img):
    """Find egg contour and return bounding box."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    return (x, y, x + w, y + h)

def convert_to_yolo(img_path, output_label, img_w, img_h):
    """Convert bbox to YOLO format."""
    img = cv2.imread(str(img_path))
    if img is None:
        return False
    
    bbox = find_egg_contour(img)
    if bbox is None:
        x1, y1, x2, y2 = 0, 0, img_w, img_h
    else:
        x1, y1, x2, y2 = bbox
    
    x_center = ((x1 + x2) / 2) / img_w
    y_center = ((y1 + y2) / 2) / img_h
    box_w = (x2 - x1) / img_w
    box_h = (y2 - y1) / img_h
    
    with open(output_label, 'w') as f:
        f.write(f"0 {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}\n")
    return True

def main():
    # Create directories
    for split in ['train', 'val', 'test']:
        os.makedirs(f"{OUTPUT_BASE}/images/{split}", exist_ok=True)
        os.makedirs(f"{OUTPUT_BASE}/labels/{split}", exist_ok=True)
    
    # Get all images
    damaged = list(Path(DAMAGED_DIR).glob("*.jpg"))
    not_damaged = list(Path(NOT_DAMAGED_DIR).glob("*.jpg"))
    all_images = damaged + not_damaged
    
    print(f"Total images: {len(all_images)}")
    
    # Shuffle and split
    np.random.seed(42)
    indices = np.random.permutation(len(all_images))
    train_idx = indices[:int(0.7 * len(all_images))]
    val_idx = indices[int(0.7 * len(all_images)):int(0.85 * len(all_images))]
    test_idx = indices[int(0.85 * len(all_images)):]
    
    splits = {'train': train_idx, 'val': val_idx, 'test': test_idx}
    
    for split_name, idx_list in splits.items():
        print(f"Processing {split_name} ({len(idx_list)} images)...")
        for i, idx in enumerate(idx_list):
            img_path = all_images[idx]
            
            # Copy image
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            h, w = img.shape[:2]
            dest_img = f"{OUTPUT_BASE}/images/{split_name}/{img_path.name}"
            cv2.imwrite(dest_img, img)
            
            # Create label
            dest_label = f"{OUTPUT_BASE}/labels/{split_name}/{img_path.stem}.txt"
            convert_to_yolo(img_path, dest_label, w, h)
            
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(idx_list)}")
    
    # Create data.yaml
    data_config = {
        'path': os.path.abspath(OUTPUT_BASE),
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'nc': 1,
        'names': {0: 'egg'}
    }
    with open(f"{OUTPUT_BASE}/data.yaml", 'w') as f:
        yaml.dump(data_config, f)
    
    print("\nDone! Dataset created:")
    print(f"  Train: {len(train_idx)}")
    print(f"  Val: {len(val_idx)}")
    print(f"  Test: {len(test_idx)}")
    print("\nNext: python src/train_yolo.py --train")

if __name__ == "__main__":
    main()