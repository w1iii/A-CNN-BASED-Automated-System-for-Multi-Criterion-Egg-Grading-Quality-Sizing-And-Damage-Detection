"""
Camera Calibration Utility for Egg Detection System

This script helps you calibrate the camera's mm-per-pixel ratio for accurate
size and weight measurement. You'll need a reference object of known size
(e.g., a ruler or a standard egg).

Usage:
    python3 calibrate_camera.py --source 0
    
    Place your reference object in front of the camera
    1. Press 'R' to capture reference object region
    2. The script will measure the width in pixels
    3. Enter the actual size of your reference object in mm
    4. Calibration factor will be computed and saved to config.yaml
"""

import cv2
import yaml
import argparse


def calibrate_camera(camera_index=0):
    """Interactive camera calibration."""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Failed to open camera {camera_index}")
        return
    
    print("\n" + "="*60)
    print("Camera Calibration Tool")
    print("="*60)
    print("\nInstructions:")
    print("1. Place your reference object (ruler, known-size card) in front of camera")
    print("2. Press 'R' to start drawing the bounding box")
    print("3. Click and drag to select the object region")
    print("4. Press ENTER to confirm selection")
    print("5. Enter the actual size of the reference object in millimeters")
    print("\nControls:")
    print("- R: Capture and measure reference object")
    print("- Q: Quit without saving")
    print("- S: Save calibration to config.yaml")
    print("="*60 + "\n")
    
    selected_region = None
    drawing = False
    start_point = None
    mm_per_pixel = 1.0
    
    def draw_rectangle(event, x, y, flags, param):
        nonlocal selected_region, drawing, start_point
        
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start_point = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            if drawing:
                pass  # Will draw in display loop
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            if start_point:
                selected_region = (start_point[0], start_point[1], x, y)
    
    cv2.namedWindow("Calibration Frame")
    cv2.setMouseCallback("Calibration Frame", draw_rectangle)
    
    calibration_done = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        display_frame = frame.copy()
        
        # Draw current selection box if drawing
        if drawing and start_point:
            x1, y1 = start_point
            # Get current mouse position by reading the frame again
            # (we'll use the selected_region if it exists)
            pass
        
        # Draw confirmed selection
        if selected_region:
            x1, y1, x2, y2 = selected_region
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Calculate width
            width_px = abs(x2 - x1)
            cv2.putText(display_frame, f"Width: {width_px}px", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if calibration_done:
                width_mm = width_px * mm_per_pixel
                cv2.putText(display_frame, f"Size: {width_mm:.1f}mm", (x1, y1 - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Show instructions
        instructions = [
            "R: Measure | S: Save | Q: Quit",
            f"mm/pixel: {mm_per_pixel:.4f}" if calibration_done else "measuring..."
        ]
        for i, text in enumerate(instructions):
            cv2.putText(display_frame, text, (10, 30 + i*30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow("Calibration Frame", display_frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("Calibration cancelled.")
            break
        elif key == ord('r'):
            print("\nDraw a rectangle around your reference object, then press ENTER")
            selected_region = None
            drawing = False
            
            # Wait for user to draw
            def draw_callback(event, x, y, flags, param):
                nonlocal selected_region, drawing, start_point
                if event == cv2.EVENT_LBUTTONDOWN:
                    drawing = True
                    start_point = (x, y)
                elif event == cv2.EVENT_LBUTTONUP:
                    drawing = False
                    if start_point:
                        selected_region = (min(start_point[0], x), min(start_point[1], y),
                                         max(start_point[0], x), max(start_point[1], y))
            
            cv2.setMouseCallback("Calibration Frame", draw_callback)
            
            # Wait for selection
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                disp = frame.copy()
                
                # Draw current box while dragging
                if drawing and start_point:
                    cv2.rectangle(disp, start_point, (0, 255, 0), 2)
                
                if selected_region:
                    x1, y1, x2, y2 = selected_region
                    cv2.rectangle(disp, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    width_px = abs(x2 - x1)
                    cv2.putText(disp, f"Width: {width_px}px | Press ENTER to confirm",
                               (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow("Calibration Frame", disp)
                k = cv2.waitKey(1) & 0xFF
                
                if k == 13:  # ENTER key
                    if selected_region:
                        break
                elif k == ord('q'):
                    selected_region = None
                    break
            
            if selected_region:
                x1, y1, x2, y2 = selected_region
                width_px = abs(x2 - x1)
                
                # Ask user for actual size
                print(f"\nMeasured width: {width_px} pixels")
                try:
                    actual_size_mm = float(input("Enter actual size of reference object (mm): "))
                    if actual_size_mm > 0 and width_px > 0:
                        mm_per_pixel = actual_size_mm / width_px
                        calibration_done = True
                        print(f"Calibration: {mm_per_pixel:.6f} mm/pixel")
                        print(f"(For reference: 50mm object at {width_px}px → {mm_per_pixel:.6f} mm/px)")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        
        elif key == ord('s') and calibration_done:
            # Save calibration to config
            try:
                config_path = "config/config.yaml"
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                if 'calibration' not in config:
                    config['calibration'] = {}
                
                config['calibration']['mm_per_pixel'] = round(mm_per_pixel, 6)
                
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                print(f"\n✓ Calibration saved!")
                print(f"  mm_per_pixel: {mm_per_pixel:.6f}")
                print(f"  Saved to: {config_path}")
                break
            except Exception as e:
                print(f"Error saving calibration: {e}")
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Camera Calibration Tool")
    parser.add_argument("--source", type=str, default="0",
                        help="Camera index (0, 1, ...) or video file path")
    args = parser.parse_args()
    
    try:
        source = int(args.source)
    except ValueError:
        source = args.source
    
    calibrate_camera(source)
