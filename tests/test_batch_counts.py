import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.models import DetectionBox, Prediction
from app.services.prediction_service import classify_batch_counts


class BatchCountTests(unittest.TestCase):
    def test_counts_are_mutually_exclusive_with_damage_precedence(self):
        prediction = Prediction(
            user_id=1,
            file_name="tray.jpg",
            file_path="/tmp/tray.jpg",
            file_type="image",
        )
        prediction.detection_boxes = [
            DetectionBox(
                damage_status="Damaged",
                cleanliness_status="Stained",
                requires_review=False,
            ),
            DetectionBox(
                damage_status="Not Damaged",
                cleanliness_status="Stained",
                requires_review=False,
            ),
            DetectionBox(
                damage_status="Not Damaged",
                cleanliness_status="Clean",
                requires_review=False,
            ),
            DetectionBox(
                damage_status="Needs Review",
                cleanliness_status="Clean",
                requires_review=True,
            ),
        ]

        self.assertEqual(
            classify_batch_counts(prediction),
            {"okay": 1, "stained": 1, "damaged": 1, "review": 1},
        )
