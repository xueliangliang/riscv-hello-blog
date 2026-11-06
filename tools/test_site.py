#!/usr/bin/env python3
"""Build real Hugo output and check branding, navigation and taxonomy links."""

from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def find(self, tag=None, css=None):
        found = []
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag == tag) and (css is None or css in child.attrs.get('class', '').split()):
                    found.append(child)
                found.extend(child.find(tag, css))
        return found

    def text(self):
        return ''.join(child.text() if isinstance(child, Node) else child for child in self.children)


class Document(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        child = Node(tag, attrs)
        self.stack[-1].children.append(child)
        if tag not in self.VOID:
            self.stack.append(child)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def build(source, destination, success=True):
    result = subprocess.run(['hugo', '--minify', '--source', str(source), '--destination', str(destination)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if success and result.returncode:
        raise AssertionError(result.stdout)
    return result


def page(site, route):
    return Document((site / unquote(route).lstrip('/') / 'index.html').read_text()).root


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='xll-site-test-', dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.site = Path(cls.temporary.name) / 'site'
        build(ROOT, cls.site)
        metadata = [tomllib.loads(path.read_text().split('+++', 2)[1])
                    for path in (ROOT / 'content/posts').glob('*.md') if path.name != '_index.md']
        cls.posts = [post for post in metadata if not post.get('draft', False)
                     and post['date'] <= datetime.now().astimezone()]
        cls.series = tomllib.loads((ROOT / 'data/series.toml').read_text())

    def test_home_brand_feature_and_chronological_order(self):
        home = page(self.site, '/')
        self.assertEqual(home.find('title')[0].text(), 'XLL技术笔记')
        hero = home.find(css='hero')[0]
        self.assertEqual(hero.find('h1')[0].text(), '序篇：为什么开始')
        self.assertEqual(hero.find(css='hero-link')[0].attrs['href'], '/posts/why-this-series/')
        self.assertEqual(hero.find(css='hero-secondary')[0].attrs['href'], '/series/')
        cards = home.find(css='post-card')
        expected = sorted(self.posts, key=lambda post: post['date'], reverse=True)
        self.assertEqual([card.find('h3')[0].find('a')[0].attrs['href'] for card in cards],
                         ['/posts/' + post['slug'] + '/' for post in expected])
        self.assertEqual(home.find('h2')[0].text(), '最新文章')
        self.assertNotIn('https://github.com/xueliangliang/riscv-hello',
                         [anchor.attrs.get('href') for anchor in home.find(css='site-nav')[0].find('a')])

    def test_navigation_and_repository_locations_are_consistent(self):
        def navigation(document):
            menus = document.find(css='site-nav')
            self.assertEqual(len(menus), 1)
            return [(anchor.text(), anchor.attrs.get('href')) for anchor in menus[0].find('a')]

        expected = navigation(page(self.site, '/'))
        self.assertTrue(expected)
        repositories = {series['code_repository_url'] for series in self.series.values()
                        if series.get('code_repository_url')}
        for path in self.site.rglob('*.html'):
            with self.subTest(page=str(path.relative_to(self.site))):
                document = Document(path.read_text()).root
                self.assertEqual(navigation(document), expected)
                for header in document.find('header'):
                    self.assertFalse(repositories.intersection(anchor.attrs.get('href') for anchor in header.find('a')),
                                     'Series repositories belong at the end, not in a page-specific header')
        overview = page(self.site, '/series/')
        repository = self.series['riscv-os']['code_repository_url']
        links = [anchor for anchor in overview.find('a') if anchor.attrs.get('href') == repository]
        self.assertEqual(len(links), 1)
        self.assertIn(links[0], overview.find(css='article-end')[0].find('a'))

    def test_series_and_clickable_theme_labels_everywhere(self):
        for post in self.posts:
            route = '/posts/' + post['slug'] + '/'
            detail = page(self.site, route)
            series = self.series.get(post.get('series_id') or '')
            if series:
                self.assertEqual(detail.find(css='series-tag')[0].find('a')[0].attrs['href'], series['page'].rstrip('/') + '/')
                self.assertEqual(detail.find(css='series-tag')[0].text(), series['title'])
            else:
                self.assertFalse(detail.find(css='series-tag'))
            self.assertTrue(detail.find('title')[0].text().endswith(' · XLL技术笔记'))
            lists = detail.find(css='tag-list')
            labels = lists[0].find('a') if lists else []
            self.assertEqual(len(labels), len(post.get('tags', [])) + bool(series))
            for label in labels[1:] if series else labels:
                target = page(self.site, label.attrs['href'])
                self.assertIn(route, [anchor.attrs.get('href') for anchor in target.find('a')])
        for route in ['/', '/posts/', '/tags/risc-v/']:
            cards = page(self.site, route).find(css='post-card')
            expected = self.posts if route != '/tags/risc-v/' else [post for post in self.posts if 'risc-v' in [tag.casefold() for tag in post.get('tags', [])]]
            self.assertEqual(len(cards), len(expected))
        self.assertEqual(page(self.site, '/series/').find('h1')[0].text(), 'RISC-V OS实验笔记')

    def test_adsense_appears_once_in_production_heads_except_404(self):
        config = tomllib.loads((ROOT / 'hugo.toml').read_text())['params']['adsense']
        expected = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + config['client']
        enabled = bool(config.get('enabled') and config.get('client'))
        for path in self.site.rglob('*.html'):
            with self.subTest(page=str(path.relative_to(self.site))):
                document = Document(path.read_text()).root
                scripts = [script for script in document.find('script')
                           if 'pagead2.googlesyndication.com/pagead/js/adsbygoogle.js' in script.attrs.get('src', '')]
                self.assertEqual(len(scripts), 0 if path == self.site / '404.html' or not enabled else 1)
                for script in scripts:
                    self.assertIn(script, document.find('head')[0].find('script'))
                    self.assertEqual(script.attrs['src'], expected)
                    self.assertIn('async', script.attrs)
                    self.assertEqual(script.attrs['crossorigin'], 'anonymous')

    def test_adsense_disabled_and_nonproduction_builds_omit_the_script(self):
        fixture = self.fixture()
        config = fixture / 'hugo.toml'
        original = config.read_text()
        marker = '[params.adsense]\nenabled = true'
        self.assertIn('[params.adsense]', original)
        disabled = original.replace(marker, '[params.adsense]\nenabled = false')
        self.assertFalse(tomllib.loads(disabled)['params']['adsense']['enabled'])
        config.write_text(disabled)
        build(fixture, fixture / 'disabled-site')
        for path in (fixture / 'disabled-site').rglob('*.html'):
            self.assertNotIn('pagead2.googlesyndication.com', path.read_text())
        config.write_text(original.replace('[params.adsense]\nenabled = false', marker))
        for environment in ['development', 'staging']:
            destination = fixture / (environment + '-site')
            result = subprocess.run(['hugo', '--minify', '--environment', environment,
                                     '--source', str(fixture), '--destination', str(destination)],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            for path in destination.rglob('*.html'):
                self.assertNotIn('pagead2.googlesyndication.com', path.read_text())

    def test_adsense_is_not_loaded_by_the_actual_preview_server(self):
        import socket
        import time
        from urllib.error import URLError
        from urllib.request import urlopen

        fixture = self.fixture()
        config = fixture / 'hugo.toml'
        config.write_text(config.read_text().replace('[params.adsense]\nenabled = false', '[params.adsense]\nenabled = true'))
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        process = subprocess.Popen(['hugo', 'server', '--source', str(fixture),
                                    '--bind', '127.0.0.1', '--port', str(port),
                                    '--environment', 'production', '--disableLiveReload'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    self.fail(process.communicate()[0])
                try:
                    with urlopen(f'http://127.0.0.1:{port}/', timeout=1) as response:
                        self.assertEqual(response.status, 200)
                        html = response.read().decode()
                    break
                except URLError:
                    time.sleep(0.05)
            else:
                self.fail('Hugo preview server did not become ready')
            self.assertIn('XLL技术笔记', html)
            self.assertNotIn('pagead2.googlesyndication.com', html)
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)

    def test_analytics_comments_canonicals_and_feed_preserved(self):
        for post in self.posts:
            route = '/posts/' + post['slug'] + '/'
            detail = page(self.site, route)
            scripts = [script.attrs.get('src', '') for script in detail.find('script')]
            self.assertEqual(sum('googletagmanager.com/gtag/js' in src for src in scripts), 1)
            self.assertEqual(sum('giscus.app/client.js' in src for src in scripts), 1)
            giscus = next(script for script in detail.find('script') if 'giscus.app/client.js' in script.attrs.get('src', ''))
            self.assertEqual(giscus.attrs['data-mapping'], 'pathname')
            canonical = next(link for link in detail.find('link') if link.attrs.get('rel') == 'canonical')
            self.assertEqual(canonical.attrs['href'], 'https://blog.xueliangliang.dev' + route)
        self.assertIn('<title>XLL技术笔记</title>', (self.site / 'index.xml').read_text())

    def fixture(self):
        destination = Path(self.temporary.name) / self._testMethodName
        shutil.copytree(ROOT, destination,
                        ignore=shutil.ignore_patterns('.git', 'node_modules', 'public', 'resources', 'build', '__pycache__', '.hugo_build.lock'))
        return destination

    def test_other_series_and_standalone_notes_use_same_templates(self):
        fixture = self.fixture()
        with (fixture / 'data/series.toml').open('a') as output:
            output.write('\n[fixture]\ntitle="另一个系列"\npage="/another-series"\ncode_repository_url=""\n')
        overview = fixture / 'content/another-series/_index.md'
        overview.parent.mkdir()
        overview.write_text('+++\ntitle="另一个系列"\n+++\n')
        for name, series in [('standalone', ''), ('second-series', 'series_id="fixture"\n')]:
            (fixture / ('content/posts/' + name + '.md')).write_text(
                '+++\ntitle="' + name + '"\nslug="' + name + '"\ndate=2020-01-01T00:00:00+08:00\n'
                + series + 'tags=["fixturetopic"]\n+++\nFixture body.\n')
        site = fixture / 'built'
        build(fixture, site)
        self.assertFalse(page(site, '/posts/standalone/').find(css='series-tag'))
        label = page(site, '/posts/second-series/').find(css='series-tag')[0].find('a')[0]
        self.assertEqual((label.text(), label.attrs['href']), ('另一个系列', '/another-series/'))
        self.assertEqual(len(page(site, '/tags/fixturetopic/').find(css='post-card')), 2)
        self.assertEqual(len(page(self.site, '/').find(css='post-card')), len(self.posts))

    def test_unknown_series_fails_build_instead_of_misrouting(self):
        fixture = self.fixture()
        (fixture / 'content/posts/bad-series.md').write_text(
            '+++\ntitle="Bad series"\nseries_id="missing-series"\n+++\n')
        result = build(fixture, fixture / 'built', success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unknown series_id', result.stdout)


if __name__ == '__main__':
    unittest.main()
