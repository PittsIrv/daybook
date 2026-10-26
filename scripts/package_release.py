#!/usr/bin/env python3
"""Package only explicitly public source and synthetic examples, never the workspace."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.0-alpha'
FILES=['README.md','LICENSE','.gitignore','.github/workflows/checks.yml',
       'dashboard/server.py','dashboard/runtime.py','dashboard/insights.py','dashboard/manage.py',
       'dashboard/README.md','dashboard/doctor.py','dashboard/launch.py','dashboard/Start Daybook.command','dashboard/Start Demo.command',
       'dashboard/static/index.html','dashboard/static/app.js','dashboard/static/style.css',
       'shortcuts/build_shortcuts.py','shortcuts/README.md',
       'scripts/make_demo.py','scripts/package_release.py',
       'docs/RELEASING.md','docs/VERIFICATION.md','docs/demo.jpg']


def public_files():
    files=[Path(p) for p in FILES]
    files += sorted(p.relative_to(ROOT) for p in (ROOT/'dashboard/tests').glob('test_*.py'))
    examples=sorted((ROOT/'dashboard/examples').glob('*.json'))
    for p in examples:
        if json.loads(p.read_text()).get('synthetic') is not True:
            raise ValueError(f'Refusing non-synthetic example: {p.name}')
        files.append(p.relative_to(ROOT))
    return files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only',action='store_true')
    args=parser.parse_args()
    files=public_files()
    stage=ROOT/'release-source'
    marker=stage/'.daybook-release-staging'
    if stage.exists():
        if (stage/'.git').exists():
            raise SystemExit('Refusing to replace a Git checkout. Move release-source to a permanent repository folder before rebuilding.')
        if not marker.exists():
            raise SystemExit('Refusing to replace a directory without the release-staging marker')
        shutil.rmtree(stage)
    stage.mkdir()
    marker.write_text('Generated staging area. Rebuild with scripts/package_release.py.\n')
    for relative in files:
        source=ROOT/relative
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Not a regular source file: {relative}')
        content=source.read_bytes()
        if (b'/' + b'Users/') in content or (b'allDevices' + b'002016') in content:
            raise ValueError(f'Possible personal metadata: {relative}')
        target=stage/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    archive=out/f'daybook-{VERSION}{"-source" if args.source_only else ""}.zip'
    entries={str(p):(ROOT/p).read_bytes() for p in files}
    if not args.source_only:
        signed=ROOT/'shortcuts/release/Screen Time Yesterday.shortcut'
        unsigned=ROOT/'shortcuts/release/Screen Time Yesterday.unsigned.shortcut'
        if not signed.is_file() or signed.stat().st_mtime < unsigned.stat().st_mtime:
            raise SystemExit('Generate and sign the portable Shortcut first; see docs/RELEASING.md')
        import plistlib
        workflow=plistlib.loads(unsigned.read_bytes())
        for action in workflow['WFWorkflowActions']:
            if 'selectedDevice' in action.get('WFWorkflowActionParameters',{}):
                raise ValueError('Portable Shortcut must not embed a device selector')
        entries['shortcuts/Screen Time Yesterday.shortcut']=signed.read_bytes()
    manifest={'version':VERSION,'source_only':args.source_only,'files':{
        name:hashlib.sha256(content).hexdigest() for name,content in sorted(entries.items())}}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in sorted(entries.items()):
            info=zipfile.ZipInfo(f'daybook/{name}')
            info.external_attr=(0o100755 if name.endswith('.command') else 0o100644)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,content)
    manifest['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest_path=archive.with_suffix('.manifest.json')
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Packaged {len(entries)} explicit files: {archive.name}')
    print(f'Source repository staging: {stage.name}/; synthetic examples only.')

if __name__=='__main__':main()
