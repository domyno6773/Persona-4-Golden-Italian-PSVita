"""Apply the Vita compatibility fixes to an already assembled Italian patch.

Keeps approved adapted textures and native binary data. Builds a separate
data.cpk and optionally includes an existing Italian executable. Never writes
to a console or overwrites older releases.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil
import time
import cricodecs.cpk as cpk
from build_full_italian_cpk import is_arc, parse_arc, build_arc, is_pac, parse_pac, build_pac
from build_vita_bf import transplant_bf, transplant_bmd, transplant_pm1
from build_vita_tables import transplant_table, transplant_bvp, transplant_item_names, transplant_cmm_table, SHORTENED_LABELS
from vita_native_policy import approved_texture, preserve_adapted_text
from cpk_vita_metadata import preserve_metadata, verify_metadata
from battle_commands import preserve_command_texture


def repair(vita, pc, current, path, counts):
    if is_arc(vita):
        vf = parse_arc(vita)
        cf = parse_arc(current) if is_arc(current) else {}
        pf = parse_arc(pc) if pc and is_arc(pc) else {}
        rebuilt={name:repair(data,pf.get(name),cf.get(name,data),path+'/'+name,counts)
                 for name,data in vf.items()}
        return vita if rebuilt==vf else build_arc(rebuilt)
    if is_pac(vita):
        vf, order = parse_pac(vita)
        cf = parse_pac(current)[0] if is_pac(current) else {}
        pf = parse_pac(pc)[0] if pc and is_pac(pc) else {}
        rebuilt={name:repair(data,pf.get(name),cf.get(name,data),path+'/'+name,counts)
                 for name,data in vf.items()}
        return vita if rebuilt==vf else build_pac(rebuilt,order)
    lower = path.lower()
    result = vita
    category = None
    if lower.endswith('.bed') or lower.endswith('dummy.dat'):
        result, category = vita, 'native_effect_or_dummy'
    elif pc:
        if vita[8:12] == b'FLW0':
            result, category = transplant_bf(vita, pc), 'flowscript'
        elif vita[8:12] == b'MSG1':
            result, category = transplant_bmd(vita, pc)[0], 'messages'
        elif vita[8:12] == b'PMD1':
            result, category = transplant_pm1(vita, pc), 'event'
        elif lower.endswith(('aicalc.tbl', 'msg.tbl', 'encount.tbl')):
            result, category = transplant_table(vita, pc, path), 'battle_table'
        elif lower.endswith('.bvp'):
            result, category = transplant_bvp(vita, pc), 'battle_voice'
        elif lower.endswith('itemtbl.bin'):
            result, category = transplant_item_names(vita, pc), 'item_names'
        elif lower.rsplit('/',1)[-1].startswith('cmm') and lower.endswith('.dat'):
            result, category = transplant_cmm_table(vita,pc,lower), 'community_table'
    if category is None:
        commands=preserve_command_texture(vita,current,path)
        adapted=preserve_adapted_text(vita,current,path)
        if commands is not None:
            result,category=commands,'battle_commands'
        elif adapted is not None:
            result,category=adapted,'fixed_text'
        elif approved_texture(path):
            if len(vita)!=len(current) or vita[8:12]!=current[8:12]:
                raise ValueError('Adapted texture layout changed: '+path)
            result,category=current,'adapted_texture'
        elif current!=vita:
            counts['restored_unknown_native']+=1
    if category:
        counts['checked_'+category] += 1
        if result != current: counts['changed_'+category] += 1
    return result


def file_lookup(archive):
    return {'/'.join(x for x in (f.dirname, f.filename) if x).lower(): i
            for i in range(archive.file_count) for f in (archive.file_info(i),)}


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vita', default='clean_vita_data.cpk')
    parser.add_argument('--pc', default='Persona 4 Golden/data_it.cpk')
    parser.add_argument('--base', default='P4G_Italian_Patch_v1.0.3/rePatch/PCSB00245/data/data.cpk')
    parser.add_argument('--output', default='P4G_Italian_Patch_v1.0.4/rePatch/PCSB00245/data/data.cpk')
    parser.add_argument('--eboot',help='Existing Italian SELF to include alongside the data archive')
    args = parser.parse_args()
    if args.eboot and not Path(args.eboot).is_file():raise FileNotFoundError(args.eboot)
    output = Path(args.output).resolve()
    if output in [Path(x).resolve() for x in (args.vita,args.pc,args.base)]:
        raise ValueError('Output must be separate from input archives')
    if output.exists():
        raise FileExistsError(output)
    counts = collections.Counter()
    started = time.time()
    native, italian, patched = (cpk.load(x) for x in (args.vita,args.pc,args.base))
    vi, pi, mi = file_lookup(native), file_lookup(italian), file_lookup(patched)
    changed = []
    for key, native_index in vi.items():
        index=mi.get(key)
        if index is None:raise ValueError('Missing source asset: '+key)
        vf, mf = native.file_info(vi[key]), patched.file_info(index)
        # Every existing BF/BMD and effect needs validation; localized sources
        # cover all other fixes. Untranslated game assets stay in the base CPK.
        vb = native.file_bytes(vi[key])
        pb = italian.file_bytes(pi[key]) if key in pi else None
        mb = patched.file_bytes(index)
        try:
            result = repair(vb,pb,mb,key,counts)
        except Exception as exc:
            raise RuntimeError(f'Failed to adapt {key}: {exc}') from exc
        if result != mb:
            patched.replace_bytes(index,result,compress=mf.file_size != mf.extract_size)
            changed.append(key)
        if len(changed) and len(changed) % 250 == 0:
            print(f'{len(changed)} CPK entries updated',flush=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary = output.with_suffix('.building.cpk')
    print('Saving corrected archive...',dict(counts),flush=True)
    patched.save(str(temporary))
    preserve_metadata(args.vita,temporary)
    verify_metadata(args.vita,temporary)
    temporary.replace(output)
    report = {'version':'1.0.4','hardware_tested':False,'native_cpk_metadata_preserved':True,'arc_member_padding':32,'executable':'original_game_no_eboot_override','counts':dict(counts),
              'changed_cpk_entries':changed,'shortened_labels':SHORTENED_LABELS,
              'data_cpk_sha256':sha256(output),
              'elapsed_seconds':round(time.time()-started,1)}
    if args.eboot:
        executable=output.parent.parent/'eboot.bin'
        shutil.copyfile(args.eboot,executable)
        report.update(executable='existing_italian_eboot',eboot_sha256=sha256(executable))
    (output.parents[3]/'build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Complete:',output,'seconds',report['elapsed_seconds'],flush=True)


if __name__ == '__main__': main()
