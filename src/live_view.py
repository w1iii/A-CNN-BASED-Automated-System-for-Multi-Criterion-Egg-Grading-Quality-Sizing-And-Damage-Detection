import cv2
import torch
import yaml

from model import EggGradingCNN
from utils import get_transforms


def load_model(model_path, config_path):
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    model = EggGradingCNN(num_classes=cfg["model"]["num_classes"])
    model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))
    model.eval()
    return model, cfg


def predict_image(model, img, cfg):
    transform = get_transforms(train=False, img_size=cfg["data"]["img_size"])
    input_tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        output = model(input_tensor)
        pred = torch.argmax(output, 1).item()
    return pred


def main():
    model_path = "models/egg_grader.pth"
    config_path = "config/config.yaml"
    model, cfg = load_model(model_path, config_path)
    class_names = ["Damaged", "Not Damaged"]

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    print("Press <space> to grade current egg, <q> to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        # Show instructions on frame
        overlay = frame.copy()
        cv2.putText(
            overlay,
            "Press SPACE to grade this egg",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.imshow("Egg Grading Live View", overlay)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == 32:  # SPACE pressed
            # Convert to RGB for transform
            rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                pred = predict_image(model, rgb_img, cfg)
                result_str = f"Predicted Class: {class_names[pred] if pred < len(class_names) else pred}"
            except Exception as e:
                result_str = f"Error: {e}"
            # Show result on snapshot
            snapshot = frame.copy()
            cv2.putText(
                snapshot,
                result_str,
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3,
            )
            cv2.imshow("Result", snapshot)
            cv2.waitKey(1500)  # Show result for 1.5 seconds, tune as needed
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
