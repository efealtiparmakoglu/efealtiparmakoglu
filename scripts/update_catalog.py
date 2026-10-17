#!/usr/bin/env python3
"""Render the public catalog; optionally refresh its data with authenticated gh."""
import argparse
import collections
import datetime
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/repositories.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Fetch public repositories using gh')
    args = parser.parse_args()
    records = json.loads(DATA.read_text())
    owner = urlsplit(records[0]['url']).path.strip('/').split('/')[0]
    if args.refresh:
        raw = subprocess.check_output([
            'gh', 'api', '--paginate', '--slurp',
            f'users/{owner}/repos?type=owner&per_page=100',
        ], text=True)
        records = []
        for page in json.loads(raw):
            for repo in page:
                # Keep the public catalog public even when gh has private-repo access.
                if repo['private'] or repo['owner']['login'].lower() != owner.lower():
                    continue
                records.append({
                    'name': repo['name'], 'url': repo['html_url'],
                    'description': repo['description'], 'language': repo['language'],
                    'topics': repo['topics'], 'empty': repo['size'] == 0,
                })
        records.sort(key=lambda item: item['name'])
        DATA.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    names = [item['name'] for item in records]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate repository in catalog')
    groups = collections.defaultdict(list)
    for repo in records:
        expected = f"https://github.com/{owner}/{repo['name']}"
        if repo['url'] != expected:
            raise ValueError(f"Unexpected repository URL: {repo['name']}")
        group = 'Placeholders' if repo['empty'] else repo['language'] or 'Other'
        groups[group].append(repo)
    order = sorted(groups, key=lambda lang: (lang == 'Placeholders', -len(groups[lang]), lang))
    title = '# Project catalog / Proje kataloğu\n\n'
    title += f'[← Profile / Profil](https://github.com/{owner}) · [Cinema gallery / Sinema galerisi](docs/cinema-gallery.md)\n\n'
    title += 'Public repositories grouped by primary language. Descriptions explain the scope; they are not a certification of test coverage or production readiness.\n\n'
    title += 'Açık repolar ana dillerine göre gruplandı. Açıklamalar proje kapsamını anlatır; test kapsamı ya da üretime hazır olma garantisi değildir.\n\n'
    title += f'**{len(records)} public repositories** · Data snapshot: {datetime.date.today().isoformat()}\n\n'
    title += ' · '.join(f'[{lang} ({len(groups[lang])})](#{lang.lower()})' for lang in order)
    rows = [title]
    def escape(value):
        return (value or 'No description.').replace('|', '\\|').replace('\n', ' ')
    for lang in order:
        rows += [f'\n## {lang}\n', '| Project | What it does |', '| --- | --- |']
        for repo in sorted(groups[lang], key=lambda item: item['name']):
            rows.append(f"| [{repo['name']}]({repo['url']}) | {escape(repo['description'])} |")
    rows += ['\n---\n', 'Maintaining this catalog: `python3 scripts/update_catalog.py --refresh` fetches public repositories using `gh` and regenerates this page. Commit `PROJECTS.md` and `data/repositories.json` together.\n']
    (ROOT / 'PROJECTS.md').write_text('\n'.join(rows))
    print(f'Rendered {len(records)} public repositories in {len(groups)} groups.')


if __name__ == '__main__':
    main()
