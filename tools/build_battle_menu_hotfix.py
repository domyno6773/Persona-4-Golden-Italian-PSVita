"""Build v1.0.5 from working v1.0.4; change one native SPR's glyph pixels."""
from pathlib import Path
import hashlib,json,shutil
import cricodecs.cpk as cpk
from build_full_italian_cpk import parse_arc,build_arc,parse_pac
from battle_commands import localize_commands,check_command_pixels,EDITED_SPRITES
from cpk_vita_metadata import preserve_metadata,verify_metadata,append_entry_update


def main():
    release=Path('P4G_Italian_Patch_v1.0.5')
    output=release/'rePatch/PCSB00245/data/data.cpk'
    if output.exists():raise FileExistsError(output)
    base=cpk.load('P4G_Italian_Patch_v1.0.4/rePatch/PCSB00245/data/data.cpk')
    pc=cpk.load('Persona 4 Golden/data_it.cpk')
    def find(archive,path):
        return next(i for i in range(archive.file_count) if archive.file_info(i).full_path.lower()==path)
    index=find(base,'battle/panel/btlpanel.bin')
    original=base.file_bytes(index);files=parse_arc(original)
    pc_files=parse_arc(pc.file_bytes(find(pc,'battle/panel/btlpanel.bin')))
    native_spr=files['p4p_com01x2.spr']
    localized,previews=localize_commands(native_spr,pc_files['p4p_com01x2.spr'])
    check_command_pixels(native_spr,localized)
    files['p4p_com01x2.spr']=localized;rebuilt=build_arc(files)
    assert len(rebuilt)==len(original),'Native panel grew'
    assert all(data==parse_arc(rebuilt)[name] for name,data in parse_arc(original).items() if name!='p4p_com01x2.spr')
    base.replace_bytes(index,rebuilt,compress=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.building.cpk')
    print('Saving v1.0.5: native menu labels only...',flush=True)
    base.save(str(temporary));preserve_metadata('clean_vita_data.cpk',temporary)
    verify_metadata('clean_vita_data.cpk',temporary)
    appended=output.with_suffix('.appended.cpk')
    append_entry_update('P4G_Italian_Patch_v1.0.4/rePatch/PCSB00245/data/data.cpk',temporary,appended,'battle/panel/btlpanel.bin')
    temporary.unlink();appended.replace(output)
    executable=output.parent.parent/'eboot.bin'
    shutil.copy2('P4G_Italian_Patch_v1.0.4/rePatch/PCSB00245/eboot.bin',executable)
    def sha(p):
        with p.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
    report=dict(version='1.0.5',base_version='1.0.4',hardware_tested=False,
                changed_cpk_entries=['battle/panel/btlpanel.bin'],edited_text_sprites=list(EDITED_SPRITES),
                native_spr_bytes=len(native_spr),native_panel_bytes=len(original),metadata_palettes_icons_preserved=True,
                unchanged_payload_offsets_preserved=True,
                data_cpk_sha256=sha(output),eboot_sha256=sha(executable))
    (release/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
