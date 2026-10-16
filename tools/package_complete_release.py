"""Package the verified patch and all 26 subtitled movies in one ZIP."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=Path('P4G_Italian_Patch_v1.0.5'))
    parser.add_argument('--movies', type=Path, default=Path('P4G_Italian_Movies_v1.0.0.zip'))
    parser.add_argument('--output', type=Path, default=Path('P4G_Italian_Complete_v1.0.5.zip'))
    args = parser.parse_args()
    temporary = args.output.with_name(args.output.stem + '.building.zip')
    if args.output.exists() or temporary.exists():
        raise FileExistsError('Output or unfinished package already exists')
    verification = json.loads((args.folder / 'verification_report.json').read_text(encoding='utf-8'))
    if not verification['passed']:
        raise ValueError('Static verification has not passed')
    expected = {
        'rePatch/PCSB00245/data/data.cpk': verification['data_cpk_sha256'],
        'rePatch/PCSB00245/eboot.bin': verification['eboot_sha256'],
    }
    for name, sha in expected.items():
        if digest(args.folder / name) != sha:
            raise ValueError('Verified file changed: ' + name)
    with zipfile.ZipFile(args.movies) as movies:
        entries = movies.infolist()
        prefix = 'rePatch/PCSB00245/data/movie/'
        if len(entries) != 26 or len({e.filename for e in entries}) != 26:
            raise ValueError('Expected exactly 26 unique movie files')
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (str(path.parent) + '/' != prefix or path.suffix.lower() != '.mp4'
                    or '..' in path.parts or entry.is_dir()):
                raise ValueError('Unexpected movie archive entry: ' + entry.filename)
        # Reading each member checks the source ZIP CRC as well as its SHA-256.
        for entry in entries:
            with movies.open(entry) as stream:
                expected[entry.filename] = hashlib.file_digest(stream, 'sha256').hexdigest()
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED,
                             compresslevel=1, allowZip64=True) as archive:
            for source in sorted(args.folder.rglob('*')):
                if source.is_file():
                    name = source.relative_to(args.folder).as_posix()
                    if name.startswith(prefix):
                        raise ValueError('Movies already present in patch folder')
                    print('Packing', name, flush=True)
                    archive.write(source, name)
            for entry in entries:
                print('Including', entry.filename, flush=True)
                info = zipfile.ZipInfo(entry.filename, entry.date_time)
                info.compress_type = zipfile.ZIP_STORED
                with movies.open(entry) as src, archive.open(info, 'w', force_zip64=True) as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
            archive.writestr('SHA256SUMS.txt', ''.join(
                f'{sha}  {name}\n' for name, sha in sorted(expected.items())))
    print('Verifying every packaged game file and movie...', flush=True)
    with zipfile.ZipFile(temporary) as archive:
        for entry in archive.infolist():
            with archive.open(entry) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if entry.filename in expected and actual != expected[entry.filename]:
                raise ValueError('Packaged file differs: ' + entry.filename)
    temporary.replace(args.output)
    checksum = digest(args.output)
    args.output.with_suffix('.zip.sha256').write_text(
        checksum + '  ' + args.output.name + '\n', encoding='ascii')
    print(json.dumps({'file': args.output.name, 'bytes': args.output.stat().st_size,
                      'sha256': checksum, 'movies': len(entries)}, indent=2), flush=True)


if __name__ == '__main__':
    main()
