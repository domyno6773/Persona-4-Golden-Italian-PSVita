"""Package a verified local release without overwriting prior releases."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='P4G_Italian_Patch_v1.0.4')
    parser.add_argument('--output',type=Path,help='Separate output ZIP path')
    args=parser.parse_args()
    folder=Path(args.folder)
    output=args.output or (folder.with_suffix('.zip') if not folder.suffix else folder.parent/(folder.name+'.zip'))
    if output.exists(): raise FileExistsError(output)
    verification=json.loads((folder/'verification_report.json').read_text())
    if not verification['passed']: raise ValueError('Verification did not pass')
    with (folder/'rePatch/PCSB00245/data/data.cpk').open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=verification['data_cpk_sha256']:
        raise ValueError('Archive changed after verification')
    executable=folder/'rePatch/PCSB00245/eboot.bin'
    if executable.exists():
        with executable.open('rb') as stream:
            executable_digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if executable_digest!=verification.get('eboot_sha256'):
            raise ValueError('Executable changed after verification')
    started=time.time()
    temporary=output.with_suffix('.building.zip')
    # CPK entries are already compressed. Level 1 keeps packaging practical
    # without changing any game data or weakening ZIP's integrity checks.
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        for source in sorted(folder.rglob('*')):
            if source.is_file():
                name=source.relative_to(folder).as_posix()
                print('Packing',name,flush=True)
                archive.write(source,name)
    print('Checking ZIP CRCs...',flush=True)
    with zipfile.ZipFile(temporary) as archive:
        bad=archive.testzip()
        if bad: raise ValueError('Invalid ZIP member: '+bad)
    temporary.replace(output)
    with output.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n',encoding='ascii')
    print('Complete:',output,output.stat().st_size,'bytes;',round(time.time()-started,1),'seconds',flush=True)


if __name__=='__main__':main()
