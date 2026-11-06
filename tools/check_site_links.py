#!/usr/bin/env python3
"""Check generated internal file links and HTML fragment targets, offline."""
from html.parser import HTMLParser
from pathlib import Path
import argparse
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.urls = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('name'):
            self.ids.add(attrs['name'])
        for key in ('href', 'src'):
            if attrs.get(key):
                self.urls.append(attrs[key])


def check(site):
    site = site.resolve()
    pages = {path.resolve(): Links(path.read_text()) for path in site.rglob('*.html')}
    errors = []
    count = 0
    for source, page in pages.items():
        for raw in page.urls:
            url = urlsplit(raw)
            if url.scheme not in ('', 'http', 'https') or url.netloc not in ('', 'blog.xueliangliang.dev'):
                continue
            path = unquote(url.path)
            target = (site / path.lstrip('/') if path.startswith('/') else source.parent / path) if path else source
            target = target.resolve()
            if target.is_dir():
                target /= 'index.html'
            count += 1
            if not target.is_relative_to(site) or not target.is_file():
                errors.append(f'{source.relative_to(site)}: missing {raw}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'{source.relative_to(site)}: missing fragment {raw}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'{len(pages)} HTML pages; {count} internal links; no broken files or fragments')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    check(parser.parse_args().site)
