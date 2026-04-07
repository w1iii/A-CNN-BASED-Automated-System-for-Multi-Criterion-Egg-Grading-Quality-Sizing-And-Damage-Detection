# Quick Start Guide - Enhanced Egg Detection System

## Installation

1. **Install dependencies** (if not already installed):
```bash
pip install ultralytics opencv-python torch pyyaml
```

2. **Verify files exist**:
```bash
ls -l models/egg_grader.pth
ls -l runs/detect/egg_detection/train1/weights/best.pt
ls -l config/config.yaml
```

## Step 1: Camera Calibration (Optional but Recommended)

Before running detection, calibrate your camera for accurate size/weight measurement:

```bash
python3 src/calibrate_camera.py --source 0
```

**Calibration Steps**:
1. Place a reference object (ruler, known-size card, or standard egg) in front of camera
2. Press **R** to start measurement
3. Draw a rectangle around the reference object
4. Enter the actual size in millimeters
5. Press **S** to save

This creates the `mm_per_pixel` value in `config/config.yaml`.

## Step 2: Run Detection

### Basic Usage
```bash
python3 src/live_view.py
```

### With Custom Settings
```bash
# Use camera 1 instead of 0
python3 src/live_view.py --source 1

# Strict detection (fewer false positives)
python3 src/live_view.py --yolo-conf 0.75

# Strict classification (only high-confidence damage predictions)
python3 src/live_view.py --cnn-conf 0.75

# Process video file
python3 src/live_view.py --source path/to/video.mp4

# All together
python3 src/live_view.py --source 1 --yolo-conf 0.70 --cnn-conf 0.65
```

## Keyboard Controls During Detection

| Key | Action |
|-----|--------|
| **Q** | Quit program |
| **P** | Pause/Resume |
| **S** | Save screenshot |
| **+** | Increase YOLO confidence (stricter) |
| **-** | Decrease YOLO confidence (lenient) |
| **C** | Toggle CNN confidence filtering |

## Step 3: View Results

After running detection, check:

1. **Real-time display**:
   - Count: Number of eggs detected
   - Size distribution: Small/Medium/Large breakdown
   - Total weight: Sum of all eggs
   - Class: Damage classification
   - FPS: Processing speed

2. **CSV Log File** (`egg_statistics.csv`):
```bash
# View all detections
cat egg_statistics.csv

# Analyze with Python
python3 -c "
import pandas as pd
df = pd.read_csv('egg_statistics.csv')
print('Total eggs detected:', len(df))
print('Damaged eggs:', len(df[df['class'] == 'Damaged']))
print('Average weight:', df['weight_g'].mean())
print('Weight by size:')
print(df.groupby('size_category')['weight_g'].mean())
"
```

## Configuration Options

Edit `config/config.yaml`:

```yaml
detection:
  yolo_confidence: 0.65    # 0.5 = lenient, 0.9 = strict
  cnn_confidence: 0.6      # 0.5 = accept uncertain, 0.99 = very strict

calibration:
  mm_per_pixel: 1.0        # Set by calibration tool

tracking:
  max_distance: 50         # Increase if eggs disappear/reappear
  max_disappeared: 30      # Increase to wait longer for moving eggs
```

## Typical Settings

### For High-Speed Conveyor
```bash
python3 src/live_view.py --yolo-conf 0.70 --cnn-conf 0.65
# Risk: May miss some eggs at high speed
# Benefit: Fewer duplicate counts
```

### For Manual/Slow Processing
```bash
python3 src/live_view.py --yolo-conf 0.60 --cnn-conf 0.55
# Risk: More false positives
# Benefit: Won't miss any eggs
```

### For Strict Quality Control
```bash
python3 src/live_view.py --yolo-conf 0.80 --cnn-conf 0.80
# Risk: May miss uncertain/partially visible eggs
# Benefit: Only high-confidence detections and classifications
```

## Troubleshooting

### "Could not load YOLO model"
- Check: `ls runs/detect/egg_detection/train1/weights/best.pt`
- Solution: Verify YOLO training completed successfully

### "Failed to open video source"
- Camera not found: Try `--source 1` or `--source 2`
- Video file: Use full path: `--source /path/to/video.mp4`

### Too many false positives
- Press **+** during runtime to increase YOLO confidence
- Press **C** to enable CNN confidence filtering
- Edit config: increase `yolo_confidence` and `cnn_confidence`

### Counting same egg multiple times
- Reduce `max_distance` in config (currently 50 pixels)
- Increase `max_disappeared` to give tracker more time

### Weight always same value
- Run calibration: `python3 src/calibrate_camera.py`
- Check `config.yaml` `mm_per_pixel` is not 1.0

### CSV file not created
- Check write permissions in current directory
- Don't use `--no-logging` flag
- Check console for error messages

## Example Session

```bash
# Terminal 1: Calibrate camera
python3 src/calibrate_camera.py --source 0

# Terminal 2: Run detection
python3 src/live_view.py --source 0

# ... process eggs for 5 minutes ...
# ... press Q to quit ...

# Terminal 3: Analyze results
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('egg_statistics.csv')
print(f"Total eggs: {len(df)}")
print(f"Damaged: {(df['class'] == 'Damaged').sum()}")
print(f"Average weight: {df['weight_g'].mean():.1f}g")
print(f"\nSize breakdown:")
for size in ['Small', 'Medium', 'Large']:
    count = (df['size_category'] == size).sum()
    avg_weight = df[df['size_category'] == size]['weight_g'].mean()
    print(f"  {size}: {count} eggs, avg {avg_weight:.1f}g")
EOF
```

## What's New

✅ **Reduced false positives** - Higher default confidence threshold
✅ **Better classification** - CNN confidence scores with filtering
✅ **Accurate counting** - Object tracking prevents duplicates
✅ **Real-world measurements** - Camera calibration for mm/weight
✅ **Data logging** - All detections saved to CSV
✅ **Dynamic control** - Adjust settings in real-time with keyboard

## Next Steps

1. Calibrate your camera for accurate measurements
2. Start detection: `python3 src/live_view.py`
3. Adjust confidence thresholds with +/- keys if needed
4. Review results in `egg_statistics.csv`
5. Repeat for different eggs, speeds, or conditions

See `IMPROVEMENTS.md` for detailed documentation on all features.
