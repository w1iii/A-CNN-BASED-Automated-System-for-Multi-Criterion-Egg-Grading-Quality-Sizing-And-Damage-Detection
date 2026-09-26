from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = REPO_ROOT / "data" / "detection_finetune"


class DetectorArtifactTests(unittest.TestCase):
    def test_finetune_dataset_config_is_portable(self):
        config = yaml.safe_load((DATASET_ROOT / "data.yaml").read_text())

        self.assertEqual(config["path"], ".")
        self.assertEqual(config["nc"], 1)
        self.assertEqual(config["names"], ["egg"])
        for split in ("train", "val", "test"):
            self.assertTrue((DATASET_ROOT / config[split]).is_dir())

    def test_finetuned_checkpoint_is_present(self):
        checkpoint = (
            REPO_ROOT / "egg_detection" / "finetune_egg_v1" / "weights" / "best.pt"
        )

        self.assertTrue(checkpoint.is_file())

    def test_finetuned_checkpoint_is_application_default(self):
        config = (REPO_ROOT / "backend" / "app" / "config.py").read_text()
        camera = (REPO_ROOT / "src" / "live_camera.py").read_text()

        self.assertIn('"finetune_egg_v1" / "weights" / "best.pt"', config)
        self.assertIn("egg_detection/finetune_egg_v1/weights/best.pt", camera)

    def test_finetune_metadata_is_portable(self):
        config = yaml.safe_load(
            (REPO_ROOT / "egg_detection" / "finetune_egg_v1" / "args.yaml").read_text()
        )

        for key in ("model", "data", "project", "save_dir"):
            self.assertFalse(Path(config[key]).is_absolute())
            self.assertNotIn("\\", config[key])
