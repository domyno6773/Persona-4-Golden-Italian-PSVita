import struct
import unittest
from build_vita_bf import build_bmd_relative,parse_bmd,transplant_bmd,encode_reloc,replace_accents_safe
from verify_stability_hotfix import decode_relocations,check_messages
from build_vita_tables import transplant_bvp
from build_full_italian_cpk import build_arc,build_pac,merge_general_data,parse_pac,parse_arc
from build_stability_hotfix import repair
from verify_stability_hotfix import check_pair
from collections import Counter
from pathlib import Path
from cpk_vita_metadata import verify_metadata


def message(name,text=b'Text\0',speaker=65535):
    return dict(kind=0,name=name,page_count=1,speaker_id=speaker,
                page_addrs=[36],text_buf=text)


class StabilityRegressionTests(unittest.TestCase):
    def test_arc_messages_keep_next_binary_word_aligned(self):
        first=build_bmd_relative([message('A',b'Italian text\0')],[])
        second=build_bmd_relative([message('B',b'Second\0')],[])
        data=build_arc({'a.bmd':first,'b.bmd':second})
        cursor=4
        for name,body in parse_arc(data).items():
            self.assertEqual(len(body)%32,0)
            self.assertEqual((cursor+36)%4,0)
            parse_bmd(body)
            cursor+=36+len(body)
        self.assertEqual(cursor,len(data))

    def test_validator_rejects_old_arc_padding_loss(self):
        bodies={'a.bmd':build_bmd_relative([message('A')],[]),
                'b.bmd':build_bmd_relative([message('B')],[])}
        native=build_arc(bodies)
        broken=bytearray(struct.pack('<I',len(bodies)))
        for name,body in bodies.items():
            broken+=name.encode().ljust(32,b'\0')+struct.pack('<I',len(body))+body
        with self.assertRaisesRegex(AssertionError,'ARC member padding lost'):
            check_pair(native,bytes(broken),'battle/messages.arc',Counter())

    def test_empty_message_does_not_shift_next_dialog(self):
        empty=dict(kind=0,name='EMPTY',page_count=0,speaker_id=65535,page_addrs=[],text_buf=b'')
        data=build_bmd_relative([empty,message('NEXT')],[])
        parsed=parse_bmd(data)
        self.assertEqual(parsed['dialogs'][1]['text_buf'],b'Text\0')
        self.assertEqual(parsed['dialogs'][1]['dlg_offset']-parsed['dialogs'][0]['dlg_offset'],28)

    def test_relocations_at_old_run_boundaries(self):
        for count in (3,34,35,67,68,101,102,1000):
            with self.subTest(count=count):
                expected=[32+i*4 for i in range(count)]
                encoded=encode_reloc(expected,32)
                data=bytearray(32)+encoded
                struct.pack_into('<II',data,16,32,len(encoded))
                self.assertEqual(decode_relocations(data),expected)

    def test_function_arguments_are_not_accent_glyphs(self):
        data=b'\xf2\x05\x9c\xda' + b'gi\x9c\xda\0'
        self.assertEqual(replace_accents_safe(data),b'\xf2\x05\x9c\xda' + b"gia'\0")

    def test_speaker_indices_stay_native_when_pc_table_differs(self):
        v=build_bmd_relative([message('A',speaker=0),message('B',speaker=1)],[b'One',b'Two'])
        p=build_bmd_relative([message('A',b'Uno\0',1),message('B',b'Due\0',2)],[b'Extra',b'Uno',b'Due'])
        out,_,_=transplant_bmd(v,p)
        check_messages(v,out)
        self.assertEqual(parse_bmd(out)['speakers'],[b'Uno',b'Due'])

    def test_kind_change_does_not_replace_message_with_choice(self):
        v=build_bmd_relative([message('A')],[])
        choice=dict(kind=1,name='A',option_count=1,opt_addrs=[40],pattern=0,ext=0,reserved=0,text_buf=b'Choice\0')
        p=build_bmd_relative([choice],[])
        out,translated,kept=transplant_bmd(v,p)
        self.assertEqual((translated,kept),(0,1))
        self.assertEqual(parse_bmd(out)['dialogs'][0]['kind'],0)

    def test_malformed_bmd_fails_instead_of_silent_fallback(self):
        with self.assertRaises(ValueError):parse_bmd(b'bad input')

    def test_bvp_null_sentinel_is_preserved(self):
        msg=build_bmd_relative([message('A')],[])
        # Two directory entries, followed by 8-byte alignment padding.
        directory=struct.pack('<III',1,24,len(msg))+b'\0'*12
        vita=directory+msg
        pc=directory+msg
        result=transplant_bvp(vita,pc)
        self.assertEqual(result[12:24],b'\0'*12)

    def test_unknown_pc_binary_never_replaces_vita(self):
        native=b'Vita binary payload'
        self.assertEqual(merge_general_data(native,b'PC incompatible data','asset.bin'),native)
        self.assertEqual(repair(native,b'PC incompatible data',b'Previous corruption','asset.bin',Counter()),native)

    def test_pc_arc_cannot_replace_native_pac_panel(self):
        native=build_pac({'b_p_k01.spr':b'Vita texture'},['b_p_k01.spr'])
        foreign=build_arc({'b_p_k01x2.spr':b'PC HD texture'*100})
        result=repair(native,foreign,foreign,'battle/battle_pack.bin/panel/btlpanel.bin',Counter())
        self.assertEqual(result,native)
        with self.assertRaisesRegex(AssertionError,'container format changed'):
            check_pair(native,foreign,'battle/panel.bin',Counter())

    def test_empty_pc_pack_cannot_destroy_native_pack(self):
        native=build_pac({'model.gmo':b'Native model'},['model.gmo'])
        self.assertEqual(repair(native,b'\0'*256,b'\0'*256,'title/mariko.pack',Counter()),native)

    def test_old_cpk_header_regression_is_rejected(self):
        native=Path('clean_vita_data.cpk')
        old=Path('P4G_Italian_Patch_v1.0.2/rePatch/PCSB00245/data/data.cpk')
        if not native.exists() or not old.exists():self.skipTest('Requires privately extracted local game data')
        with self.assertRaisesRegex(AssertionError,'CPK header schema changed'):
            verify_metadata(native,old)


if __name__=='__main__':unittest.main()
