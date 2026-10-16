import shutil
import tempfile
import unittest
from pathlib import Path
from install_v104_delta import make_delta,apply_ranges,restore_ranges,digest


class DeltaInstallationTests(unittest.TestCase):
    def test_growing_and_shrinking_files_restore_original_tail(self):
        for new_data in [b'B'*30,b'B'*300,b'A'*129+b'APPENDED'*40]:
            with self.subTest(new_size=len(new_data)),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);before=root/'old';after=root/'new';target=root/'target'
                original=b'A'*129;before.write_bytes(original);after.write_bytes(new_data)
                target.write_bytes(original)
                plan=make_delta(before,after,root/'journal',64)
                apply_ranges(target,root/'journal',plan)
                self.assertEqual(target.read_bytes(),new_data)
                restore_ranges(target,root/'journal',plan)
                self.assertEqual(target.read_bytes(),original)

    def test_patch_and_rollback_match_complete_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);before=root/'old';after=root/'new';target=root/'target'
            original=bytes(range(256))*100
            changed=bytearray(original)
            for offset,length in [(0,5),(65,14),(127,9),(25599,1)]:
                changed[offset:offset+length]=b'X'*length
            before.write_bytes(original);after.write_bytes(changed);shutil.copyfile(before,target)
            plan=make_delta(before,after,root/'journal',block_size=64)
            apply_ranges(target,root/'journal',plan)
            self.assertEqual(target.read_bytes(),after.read_bytes())
            self.assertEqual(digest(target),plan['after_sha256'])
            restore_ranges(target,root/'journal',plan)
            self.assertEqual(target.read_bytes(),original)

    def test_wrong_original_is_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);before=root/'old';after=root/'new';target=root/'target'
            before.write_bytes(b'A'*256);after.write_bytes(b'B'+b'A'*254+b'B')
            plan=make_delta(before,after,root/'journal',64)
            corrupt=b'A'*255+b'C';target.write_bytes(corrupt)
            with self.assertRaisesRegex(ValueError,'differs from rollback'):
                apply_ranges(target,root/'journal',plan)
            self.assertEqual(target.read_bytes(),corrupt)

    def test_truncated_update_restores_every_original_range(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);before=root/'old';after=root/'new';target=root/'target'
            original=b'A'*256
            before.write_bytes(original);after.write_bytes(b'B'+b'A'*254+b'B')
            plan=make_delta(before,after,root/'journal',64)
            (root/'journal/after.bin').write_bytes(b'B')
            target.write_bytes(original)
            with self.assertRaisesRegex(ValueError,'Truncated update'):
                apply_ranges(target,root/'journal',plan)
            self.assertEqual(target.read_bytes(),original)


if __name__=='__main__':unittest.main()
