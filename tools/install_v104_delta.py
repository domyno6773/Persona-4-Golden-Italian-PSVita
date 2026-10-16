"""Install the verified v1.0.4 CPK using a reversible binary delta.

The two complete local CPKs remain the authoritative rollback and target.
The Vita file stays under a staging name until its full SHA-256 matches.
No installed game files or savedata are modified.
"""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
import time

OLD_HASH='bbe85da44a19d528201204d9b7a3f812b25d0ffe6785456c3ba43dfbe940bd8c'
NEW_HASH='cfa1e6370b942511a124bbddcf81cc3328a8c63a074ca52f75f7be1e9d4d3d01'
EBOOT_HASH='0e9a3d4924fd07d3a7e326585b26ba566a8206a26514b1cc201566a7988e79d5'


def digest(path,label=''):
    h=hashlib.sha256();done=0;last=time.monotonic();total=path.stat().st_size
    with path.open('rb') as stream:
        while block:=stream.read(8*1024*1024):
            h.update(block);done+=len(block)
            if label and time.monotonic()-last>=20:
                print(f'{label}: {done/total:.0%}',flush=True);last=time.monotonic()
    return h.hexdigest()


def make_delta(before,after,directory,block_size=65536):
    directory.mkdir(exist_ok=False)
    ranges=[];offset=old_offset=new_offset=0;old_hash=hashlib.sha256();new_hash=hashlib.sha256()
    with before.open('rb') as a,after.open('rb') as b, \
            (directory/'before.bin').open('xb') as old_blob, \
            (directory/'after.bin').open('xb') as new_blob:
        while True:
            x=a.read(block_size);y=b.read(block_size)
            if not x and not y:break
            old_hash.update(x);new_hash.update(y)
            if x!=y:
                start=next((i for i,(u,v) in enumerate(zip(x,y)) if u!=v),min(len(x),len(y)))
                old_end,new_end=len(x),len(y)
                if len(x)==len(y):
                    suffix=next(i for i,(u,v) in enumerate(zip(reversed(x),reversed(y))) if u!=v)
                    old_end-=suffix;new_end-=suffix
                old_part=x[start:old_end];new_part=y[start:new_end]
                old_blob.write(old_part);new_blob.write(new_part)
                ranges.append(dict(offset=offset+start,before_length=len(old_part),after_length=len(new_part),
                                   before_blob_offset=old_offset,after_blob_offset=new_offset))
                old_offset+=len(old_part);new_offset+=len(new_part)
            offset+=block_size
    plan=dict(bytes=before.stat().st_size,after_bytes=after.stat().st_size,
              before_sha256=old_hash.hexdigest(),after_sha256=new_hash.hexdigest(),
              changed_bytes=new_offset,ranges=ranges)
    (directory/'delta.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
    return plan


def restore_ranges(target,directory,plan):
    with target.open('r+b') as writer,(directory/'before.bin').open('rb') as source:
        for r in plan['ranges']:
            length=r.get('before_length',r.get('length'))
            source.seek(r.get('before_blob_offset',r.get('blob_offset')));writer.seek(r['offset'])
            block=source.read(length)
            if len(block)!=length:raise ValueError('Truncated rollback journal')
            writer.write(block)
        writer.truncate(plan['bytes'])
        writer.flush();os.fsync(writer.fileno())


def apply_ranges(target,directory,plan):
    if target.stat().st_size!=plan['bytes']:raise ValueError('Target size changed')
    # Check every affected range before the first write, even though the
    # installer also verifies the complete original file beforehand.
    with target.open('rb') as target_stream,(directory/'before.bin').open('rb') as old:
        for r in plan['ranges']:
            length=r.get('before_length',r.get('length'))
            target_stream.seek(r['offset']);old.seek(r.get('before_blob_offset',r.get('blob_offset')))
            if target_stream.read(length)!=old.read(length):
                raise ValueError('Target differs from rollback journal')
    try:
        with target.open('r+b') as writer,(directory/'after.bin').open('rb') as new:
            for r in plan['ranges']:
                length=r.get('after_length',r.get('length'))
                writer.seek(r['offset']);new.seek(r.get('after_blob_offset',r.get('blob_offset')))
                data=new.read(length)
                if len(data)!=length:raise ValueError('Truncated update journal')
                writer.write(data)
            writer.truncate(plan.get('after_bytes',plan['bytes']))
            writer.flush();os.fsync(writer.fileno())
    except Exception:
        restore_ranges(target,directory,plan)
        raise


def install_release(before_version='1.0.3',after_version='1.0.4',before_hash=OLD_HASH,after_hash=NEW_HASH,eboot_hash=EBOOT_HASH):
    root=Path.cwd().resolve()
    old=root/f'P4G_Italian_Patch_v{before_version}/rePatch/PCSB00245/data/data.cpk'
    new=root/f'P4G_Italian_Patch_v{after_version}/rePatch/PCSB00245/data/data.cpk'
    report=json.loads((root/f'P4G_Italian_Patch_v{after_version}/verification_report.json').read_text())
    if not report['passed'] or report['data_cpk_sha256']!=after_hash or report.get('eboot_sha256')!=eboot_hash:
        raise ValueError('Release has not passed verification')
    device=Path('E:/rePatch/PCSB00245').resolve(strict=True)
    if str(device).lower()!='e:\\repatch\\pcsb00245':raise ValueError('Unexpected destination')
    if not Path('E:/app/PCSB00245/sce_sys/param.sfo').is_file():raise ValueError('Wrong device/title')
    target=(device/'data/data.cpk').resolve(strict=True)
    if target.parent!=device/'data':raise ValueError('Unexpected CPK destination')
    stage=target.with_name(f'data.cpk.v{after_version}.installing')
    eboot=device/'eboot.bin';disabled=device/'eboot.bin.off'
    if stage.exists():raise FileExistsError('Device state changed')
    enable_eboot=not eboot.exists()
    if digest(disabled if enable_eboot else eboot)!=eboot_hash:raise ValueError('Unexpected Italian executable')
    journal=root/('PSVita_installazione_v'+after_version.replace('.','')+'_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    plan=make_delta(old,new,journal)
    if plan['before_sha256']!=before_hash or plan['after_sha256']!=after_hash:
        raise ValueError('Local CPK source or target changed')
    state=dict(version=after_version,status='verifying_original',target=str(target),
               staging=str(stage),full_local_rollback=str(old),journal=str(journal),
               changed_bytes=plan['changed_bytes'],savedata_untouched=True)
    def save():
        (journal/'installation.json').write_text(json.dumps(state,indent=2),encoding='utf8')
    save()
    print('Delta bytes:',plan['changed_bytes'],'ranges:',len(plan['ranges']),flush=True)
    if digest(target,'Verify installed v'+before_version)!=before_hash:
        state['status']='refused_original_mismatch';save()
        raise ValueError('Installed CPK does not match expected base; no device files changed')
    state['status']='applying_to_inactive_file';save()
    target.rename(stage)
    try:
        apply_ranges(stage,journal,plan)
        state['status']='verifying_updated_file';save()
        if digest(stage,'Verify complete v'+after_version)!=after_hash:
            raise ValueError('Updated Vita CPK failed verification')
        stage.rename(target)
    except Exception:
        state['status']='restoring_previous_cpk';save()
        if stage.exists():
            restore_ranges(stage,journal,plan)
            if digest(stage,'Verify rollback')!=before_hash:
                state['status']='rollback_requires_attention';save()
                raise RuntimeError('Rollback checksum failed; staging file left inactive')
            stage.rename(target)
        state['status']='rolled_back';save()
        raise
    state['status']='data_verified_reactivating_italian_eboot';save()
    if enable_eboot:disabled.rename(eboot)
    state.update(status='installed_and_verified',data_cpk_sha256=after_hash,
                 eboot_sha256=eboot_hash,movies_changed=False)
    save()
    print('INSTALLED AND VERIFIED',target,flush=True)
    print('ITALIAN EXECUTABLE RESTORED',eboot,flush=True)
    print('ROLLBACK JOURNAL',journal,flush=True)


def main():install_release()


if __name__=='__main__':main()
