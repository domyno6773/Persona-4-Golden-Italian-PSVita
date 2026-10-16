"""Install v1.0.3 data only, retaining the previous CPK on the Vita."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT=Path.cwd().resolve()
if not (ROOT/"P4G_Italian_Patch_v1.0.3").exists():
    ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'P4G_Italian_Patch_v1.0.3/rePatch/PCSB00245/data/data.cpk'
DESTINATION=Path('E:/rePatch/PCSB00245')
EXPECTED='bbe85da44a19d528201204d9b7a3f812b25d0ffe6785456c3ba43dfbe940bd8c'
CHUNK=4*1024*1024


def digest(path,label):
    value=hashlib.sha256();last=time.monotonic();done=0;total=path.stat().st_size
    with path.open('rb') as stream:
        while block:=stream.read(CHUNK):
            value.update(block);done+=len(block)
            if time.monotonic()-last>=20:
                print(f'{label}: {done/total:.0%}',flush=True);last=time.monotonic()
    return value.hexdigest()


def main():
    destination=DESTINATION.resolve(strict=True)
    if str(destination).lower()!='e:\\repatch\\pcsb00245':raise ValueError('Unexpected destination')
    if not Path('E:/app/PCSB00245/sce_sys/param.sfo').is_file():raise ValueError('Wrong connected device/title')
    report=json.loads((ROOT/'P4G_Italian_Patch_v1.0.3/verification_report.json').read_text())
    if not report['passed'] or report['data_cpk_sha256']!=EXPECTED or digest(SOURCE,'Verify local source')!=EXPECTED:
        raise ValueError('Hotfix verification failed')
    target=(destination/'data/data.cpk').resolve(strict=True)
    if target.parent!=destination/'data':raise ValueError('Unexpected resolved target')
    temporary=target.with_name('data.cpk.v1.0.3.installing')
    previous=target.with_name('data.cpk.pre_v1.0.3.bak')
    if temporary.exists() or previous.exists():raise FileExistsError('A staged install or backup already exists')
    if shutil.disk_usage(destination).free<SOURCE.stat().st_size+16*1024*1024:
        raise ValueError('Insufficient staging space on Vita')
    log=ROOT/('PSVita_installazione_v1.0.3_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.json')
    manifest={'version':'1.0.3','status':'copying','target':str(target),'previous_file_backup_on_device':str(previous),
              'expected_sha256':EXPECTED,'original_game_executable':True,'movies_changed':False}
    def save():log.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    save()
    done=0;last=time.monotonic();value=hashlib.sha256()
    print('Copying v1.0.3; previous CPK remains installed until verification.',flush=True)
    with SOURCE.open('rb') as reader,temporary.open('xb') as writer:
        while block:=reader.read(CHUNK):
            writer.write(block);value.update(block);done+=len(block)
            if time.monotonic()-last>=20:
                print(f'Transfer: {done/SOURCE.stat().st_size:.0%}',flush=True);last=time.monotonic()
        writer.flush();os.fsync(writer.fileno())
    if value.hexdigest()!=EXPECTED or temporary.stat().st_size!=SOURCE.stat().st_size:
        raise ValueError('Copy size/source checksum changed')
    manifest['status']='verifying_device';save()
    print('Reading back the Vita copy for SHA-256 verification...',flush=True)
    actual=digest(temporary,'Verify Vita')
    if actual!=EXPECTED:raise ValueError('Device copy checksum mismatch; original was not replaced')
    eboot=destination/'eboot.bin'
    if eboot.exists():
        disabled=destination/'eboot.bin.pre_v1.0.3.disabled'
        if disabled.exists():raise FileExistsError(disabled)
        eboot.rename(disabled)
        manifest['disabled_eboot']=str(disabled)
    manifest['status']='committing';save()
    target.rename(previous)
    try:os.replace(temporary,target)
    except Exception:
        previous.rename(target)
        raise
    manifest['status']='installed_and_verified';manifest['verified_sha256']=actual
    manifest['installed_bytes']=target.stat().st_size;save()
    print('INSTALLED AND VERIFIED:',target,flush=True)
    print('ROLLBACK COPY:',previous,flush=True)
    print('REPORT:',log,flush=True)


if __name__=='__main__':main()
