import unittest
from pathlib import Path
import cricodecs.cpk as cpk
from build_full_italian_cpk import parse_arc
from battle_commands import localize_commands,check_command_pixels,texture_info,allowed_pixel_masks


class NativeBattleCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Path('clean_vita_data.cpk').exists() or not Path('Persona 4 Golden/data_it.cpk').exists():
            raise unittest.SkipTest('Requires privately extracted native and Italian assets')
        def sprite(path):
            archive=cpk.load(path)
            i=next(i for i in range(archive.file_count) if archive.file_info(i).full_path.lower()=='battle/panel/btlpanel.bin')
            return parse_arc(archive.file_bytes(i))['p4p_com01x2.spr']
        cls.native=sprite('clean_vita_data.cpk');cls.pc=sprite('Persona 4 Golden/data_it.cpk')
        cls.localized,_=localize_commands(cls.native,cls.pc)

    def test_fixed_native_size_and_sprite_metadata(self):
        self.assertEqual(len(self.localized),len(self.native))
        first_texture=texture_info(self.native,0)[0]
        self.assertEqual(self.localized[:first_texture],self.native[:first_texture])
        self.assertTrue(check_command_pixels(self.native,self.localized))

    def test_palette_change_is_rejected(self):
        corrupted=bytearray(self.localized);off,*_=texture_info(self.native,3)
        corrupted[off+0x40]^=1
        with self.assertRaisesRegex(ValueError,'palette'):
            check_command_pixels(self.native,corrupted)

    def test_unrelated_icon_pixel_is_rejected(self):
        corrupted=bytearray(self.localized);off,w,h,_=texture_info(self.native,3)
        # A pixel in the large circular command decoration, outside all labels.
        pos=off+0x80+(50*w+350)//2
        self.assertNotIn(pos,allowed_pixel_masks(self.native))
        corrupted[pos]^=1
        with self.assertRaisesRegex(ValueError,'unrelated pixels'):
            check_command_pixels(self.native,corrupted)

    def test_pc_hd_sprite_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'size changed'):
            check_command_pixels(self.native,self.pc)


if __name__=='__main__':unittest.main()
