import json
import tempfile
import unittest
from pathlib import Path

from backup_ops import backup_path, save_backup_record


class TestBackupOperations(unittest.TestCase):
    def test_file_backup_preserves_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sample.log"
            source.write_text("ERROR 测试内容\n", encoding="utf-8")

            target = backup_path(source, root / "backups")

            self.assertTrue(target.is_file())
            self.assertEqual(target.name, source.name)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            self.assertTrue(source.is_file())

    def test_directory_backup_preserves_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "demo"

            (source / "subdir").mkdir(parents=True)
            (source / "empty").mkdir()

            (source / "sample.log").write_text(
                "INFO started\n",
                encoding="utf-8"
            )
            (source / "subdir" / "config.json").write_text(
                '{"enabled": true}\n',
                encoding="utf-8"
            )

            target = backup_path(source, root / "backups")

            self.assertTrue(target.is_dir())
            self.assertTrue((target / "empty").is_dir())

            self.assertEqual(
                (target / "sample.log").read_bytes(),
                (source / "sample.log").read_bytes()
            )
            self.assertEqual(
                (target / "subdir" / "config.json").read_bytes(),
                (source / "subdir" / "config.json").read_bytes()
            )

    def test_directory_backup_rejects_destination_inside_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "demo"
            source.mkdir()

            destinations = [
                source,
                source / "backups"
            ]

            for destination in destinations:
                with self.subTest(destination=str(destination)):
                    with self.assertRaises(ValueError):
                        backup_path(source, destination)

            self.assertFalse((source / "backups").exists())

    def test_backup_record_contains_expected_information(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sample.log"
            source.write_text("INFO started\n", encoding="utf-8")

            target = backup_path(source, root / "backups")
            record_path = save_backup_record(source, target)

            record = json.loads(
                record_path.read_text(encoding="utf-8")
            )

            self.assertEqual(
                record_path.parent,
                target.parent
            )
            self.assertEqual(
                record["source_path"],
                str(source.resolve())
            )
            self.assertEqual(
                record["target_path"],
                str(target.resolve())
            )
            self.assertEqual(record["source_type"], "file")
            self.assertEqual(record["status"], "completed")
            self.assertTrue(record["recorded_at"])