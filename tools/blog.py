#!/usr/bin/env python3
"""Local authoring workflow. Never commits, uploads, or changes cloud resources."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from check_site_links import check as check_links

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')


def read_post(path):
    raw = path.read_text()
    pieces = raw.split('+++', 2)
    if len(pieces) != 3 or pieces[0].strip():
        raise ValueError(f'{path}: expected TOML front matter')
    return {'path': path, 'meta': tomllib.loads(pieces[1]), 'raw': raw}


def registry(root):
    return tomllib.loads((root / 'data/series.toml').read_text())


def validate(root=ROOT):
    series = registry(root)
    slots = {}
    for name, definition in series.items():
        page = definition.get('page', '')
        if not definition.get('title') or not page.startswith('/') or '..' in page.split('/'):
            raise ValueError(f'{name}: invalid series title/page')
        if not (root / 'content' / page.lstrip('/') / '_index.md').is_file():
            raise ValueError(f'{name}: overview page does not exist: {page}')
        used = set()
        part_ids = set()
        for part in definition.get('parts', []):
            first, last = part.get('first'), part.get('last')
            if type(first) is not int or type(last) is not int or first < 0 or last < first:
                raise ValueError(f'{name}: invalid roadmap range')
            if not part.get('id') or part['id'] in part_ids:
                raise ValueError(f'{name}: duplicate/empty roadmap part ID')
            part_ids.add(part['id'])
            for number in range(first, last + 1):
                if number in used:
                    raise ValueError(f'{name}: overlapping roadmap order {number}')
                used.add(number)
        slots[name] = used
    posts = [read_post(path) for path in sorted((root / 'content/posts').rglob('*.md'))
             if path.name != '_index.md']
    slugs = set()
    orders = set()
    tag_spellings = {}
    now = datetime.now().astimezone()
    for post in posts:
        meta = post['meta']
        slug = meta.get('slug', '')
        if not SLUG.fullmatch(slug) or slug in slugs:
            raise ValueError(f'{post["path"]}: invalid/duplicate slug {slug!r}')
        slugs.add(slug)
        if not isinstance(meta.get('title'), str) or not meta['title'].strip():
            raise ValueError(f'{slug}: title is required')
        if type(meta.get('draft', False)) is not bool or type(meta.get('series_confirmed', False)) is not bool:
            raise ValueError(f'{slug}: draft/series_confirmed must be booleans')
        date = meta.get('date')
        if not isinstance(date, datetime) or date.utcoffset() is None:
            raise ValueError(f'{slug}: date must include a timezone')
        if not meta.get('draft', False) and not str(meta.get('description', '')).strip():
            raise ValueError(f'{slug}: a published post needs a description')
        tags = meta.get('tags', [])
        if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
            raise ValueError(f'{slug}: tags must be nonempty strings in a list')
        for tag in tags:
            tag_spellings.setdefault(tag.casefold(), set()).add(tag)
        name = meta.get('series_id')
        order = meta.get('series_order')
        if name is not None and name not in series:
            raise ValueError(f'{slug}: unknown series_id {name!r}')
        if name and slots[name] and order is None:
            raise ValueError(f'{slug}: ordered series needs series_order')
        if order is not None:
            if not name or type(order) is not int or order < 0:
                raise ValueError(f'{slug}: invalid series_order')
            if slots[name] and order not in slots[name]:
                raise ValueError(f'{slug}: order {order} is outside the configured curriculum')
            if (name, order) in orders:
                raise ValueError(f'{slug}: duplicate series_order {order} in {name}')
            orders.add((name, order))
        if meta.get('series_confirmed') and (not name or order is None or meta.get('draft', False) or date > now):
            raise ValueError(f'{slug}: only a visible ordered-series post can be confirmed')
    # Mixed spellings otherwise let Hugo pick a different display title between
    # builds, breaking exact live-byte checks despite unchanged article content.
    canonical_terms = {read_post(path)['meta'].get('title', '').casefold()
                       for path in (root / 'content/tags').rglob('_index.md')
                       if path.parent != root / 'content/tags'}
    for tag, spellings in tag_spellings.items():
        if len(spellings) > 1 and tag not in canonical_terms:
            raise ValueError(f'Tag spellings {sorted(spellings)} need an explicit canonical term title in content/tags/')
    for name, numbers in slots.items():
        for number in numbers:
            visible = any(post['meta'].get('series_id') == name
                          and post['meta'].get('series_order') == number
                          and not post['meta'].get('draft', False)
                          and post['meta']['date'] <= now for post in posts)
            if not visible and not series[name].get('planned', {}).get(str(number)):
                raise ValueError(f'{name}: order {number} needs a planned title until publication')
    return posts


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def save_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def source_digest(root):
    paths = [root / name for name in ('hugo.toml', 'package.json', 'package-lock.json') if (root / name).is_file()]
    for directory in ('content', 'data', 'layouts', 'static', 'tools'):
        paths.extend(path for path in (root / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def file_hashes(site):
    return {str(path.relative_to(site)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(site.rglob('*')) if path.is_file()}


def build_site(root=ROOT):
    directory = root / 'build'
    directory.mkdir(exist_ok=True)
    latest = directory / 'latest.json'
    receipt = {'status': 'RUNNING', 'site': None}
    # Invalidate before validation/build: a failed run must never expose old PASS.
    save_json(latest, receipt)
    release = Path(tempfile.mkdtemp(prefix='release-', dir=directory))
    receipt['release'] = str(release)
    try:
        posts = validate(root)
        before = source_digest(root)
        site = release / 'site'
        result = subprocess.run(['hugo', '--minify', '--source', str(root), '--destination', str(site)],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (release / 'hugo.log').write_text(result.stdout)
        if result.returncode:
            raise ValueError(f'Hugo failed; see {release / "hugo.log"}')
        for required in ('index.html', 'index.xml', 'sitemap.xml', '404.html'):
            if not (site / required).is_file():
                raise ValueError(f'Hugo did not produce required output: {required}')
        for post in posts:
            meta = post['meta']
            visible = not meta.get('draft', False) and meta['date'] <= datetime.now().astimezone()
            generated = site / 'posts' / meta['slug'] / 'index.html'
            if generated.is_file() != visible:
                raise ValueError(f'Published/draft output mismatch: {meta["slug"]}')
        check_links(site)
        if source_digest(root) != before:
            raise ValueError('Source changed during build; rebuild before deployment')
        receipt.update(status='PASS', site=str(site), source_sha256=before,
                       files=file_hashes(site), post_count=len(posts),
                       built_at=datetime.now().astimezone().isoformat())
        save_json(release / 'manifest.json', receipt)
        save_json(latest, receipt)
        return receipt
    except BaseException as error:
        receipt.update(status='FAIL', error=str(error), site=None)
        save_json(release / 'manifest.json', receipt)
        save_json(latest, receipt)
        raise


def artifact(root=ROOT):
    receipt = json.loads((root / 'build/latest.json').read_text())
    if receipt.get('status') != 'PASS' or not receipt.get('site'):
        raise ValueError('No successful current build; run build first')
    if receipt['source_sha256'] != source_digest(root):
        raise ValueError('Build is stale: source changed; run build again')
    site = Path(receipt['site'])
    if not site.is_dir() or file_hashes(site) != receipt['files']:
        raise ValueError('Build output is missing or modified; run build again')
    return site


def new_post(args, root=ROOT):
    posts = validate(root)
    if not SLUG.fullmatch(args.slug) or any(post['meta']['slug'] == args.slug for post in posts):
        raise ValueError('Slug must be unique lowercase words separated by hyphens')
    if not args.title.strip():
        raise ValueError('Title must not be empty')
    if any(not tag.strip() for tag in args.tags):
        raise ValueError('Tags must not be blank')
    series = registry(root)
    if args.series and args.series not in series:
        raise ValueError('Unknown series; define it in data/series.toml first')
    if args.order is not None and not args.series:
        raise ValueError('--order requires --series')
    if args.series and series[args.series].get('parts') and args.order is None:
        raise ValueError('Ordered series requires --order')
    if args.order is not None:
        if args.order < 0 or any(post['meta'].get('series_id') == args.series
                                and post['meta'].get('series_order') == args.order for post in posts):
            raise ValueError('Series order is negative or already used')
        parts = series[args.series].get('parts', [])
        if parts and not any(part['first'] <= args.order <= part['last'] for part in parts):
            raise ValueError('Order is outside the configured curriculum')
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    lines = ['+++', 'title = ' + quote(args.title),
             'date = ' + datetime.now().astimezone().isoformat(timespec='seconds'),
             'slug = ' + quote(args.slug), 'description = ' + quote(args.description)]
    if args.series:
        lines.append('series_id = ' + quote(args.series))
    if args.order is not None:
        lines.extend(['series_order = ' + str(args.order), 'series_confirmed = false'])
    lines.extend(['tags = ' + quote(args.tags), 'draft = true', '+++', '', '## 这篇要解决什么', '', ''])
    prefix = f'{args.order:02d}-' if args.order is not None else ''
    path = root / 'content/posts' / (prefix + args.slug + '.md')
    with path.open('x', encoding='utf-8') as output:
        output.write('\n'.join(lines))
    return path


def confirm(slug, root=ROOT, allow_loopback=False):
    posts = validate(root)
    matches = [post for post in posts if post['meta']['slug'] == slug]
    if len(matches) != 1:
        raise ValueError('Unknown post slug')
    post = matches[0]
    meta = post['meta']
    if meta.get('draft', False) or meta['date'] > datetime.now().astimezone() or 'series_order' not in meta:
        raise ValueError('Confirmation requires a visible ordered-series post')
    config = tomllib.loads((root / 'hugo.toml').read_text())
    base = config['baseURL'].rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' and not (allow_loopback and parsed.hostname in ('127.0.0.1', 'localhost', '::1')):
        raise ValueError('Online confirmation requires HTTPS')
    receipt = build_site(root)
    expected = (Path(receipt['site']) / 'posts' / slug / 'index.html').read_bytes()
    url = base + '/posts/' + slug + '/'
    with urlopen(Request(url, headers={'Accept-Encoding': 'identity'}), timeout=30) as response:
        if response.status != 200 or response.geturl() != url or response.read() != expected:
            raise ValueError('Live article is not byte-identical to this build; do not confirm yet')
    if post['path'].read_text() != post['raw']:
        raise ValueError('Article changed during verification; refusing metadata update')
    start, front, body = post['raw'].split('+++', 2)
    field = 'series_confirmed = true'
    if re.search(r'(?m)^[ \t]*series_confirmed[ \t]*=', front):
        front = re.sub(r'(?m)^[ \t]*series_confirmed[ \t]*=[^\n]*', field, front, count=1)
    else:
        front += field + '\n'
    updated = start + '+++' + front + '+++' + body
    atomic_text(post['path'], updated)
    save_json(root / 'build/confirmations' / (slug + '.json'),
              {'url': url, 'article_sha256': hashlib.sha256(expected).hexdigest(),
               'confirmed_at': datetime.now().astimezone().isoformat()})
    return post['path']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    new = commands.add_parser('new', help='Create a draft, never overwrite a post')
    new.add_argument('slug')
    new.add_argument('--title', required=True)
    new.add_argument('--description', default='')
    new.add_argument('--series')
    new.add_argument('--order', type=int)
    new.add_argument('--tags', nargs='*', default=[])
    commands.add_parser('validate', help='Validate metadata, uniqueness and roadmap coverage')
    commands.add_parser('build', help='Build and link-check a fresh production directory')
    commands.add_parser('artifact', help='Print a verified current build path, or fail closed')
    confirmation = commands.add_parser('confirm', help='Verify exact live bytes before marking series progress')
    confirmation.add_argument('slug')
    args = parser.parse_args()
    try:
        if args.command == 'new':
            print(new_post(args))
        elif args.command == 'validate':
            print(f'PASS metadata: {len(validate())} posts')
        elif args.command == 'build':
            receipt = build_site()
            print('PASS production build:', receipt['site'])
        elif args.command == 'artifact':
            print(artifact())
        elif args.command == 'confirm':
            print('Live bytes verified; series metadata confirmed:', confirm(args.slug))
            print('Rebuild and deploy the overview; article bytes must remain unchanged.')
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'ERROR: {error}\n')


if __name__ == '__main__':
    main()
