"""Install only the verified v1.0.5 battle-menu update over exact v1.0.4."""
import json
from pathlib import Path
from install_v104_delta import install_release


def main():
    backup=json.loads(Path('PSVita_preparazione_v105.json').read_text())
    if not backup['verified'] or not (Path(backup['backup'])/'report.json').is_file():
        raise ValueError('A verified savedata backup is required before this install')
    install_release(before_version='1.0.4',after_version='1.0.5',
                    before_hash='cfa1e6370b942511a124bbddcf81cc3328a8c63a074ca52f75f7be1e9d4d3d01',
                    after_hash='9694e080f67cbf2f57797bf3a0eb8dbbf21805bef7b4cdc8af9e9f2b8bafebcc')


if __name__=='__main__':main()
