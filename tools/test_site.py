#!/usr/bin/env python3
"""Build real Hugo output and check branding, navigation and taxonomy links."""

from html.parser import HTMLParser
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
        cls.posts = [tomllib.loads(path.read_text().split('+++', 2)[1])
                     for path in (ROOT / 'content/posts').glob('*.md')]

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

    def test_series_and_clickable_theme_labels_everywhere(self):
        for post in self.posts:
            route = '/posts/' + post['slug'] + '/'
            detail = page(self.site, route)
            self.assertEqual(detail.find(css='series-tag')[0].find('a')[0].attrs['href'], '/series/')
            self.assertEqual(detail.find(css='series-tag')[0].text(), 'RISC-V OS实验笔记')
            self.assertTrue(detail.find('title')[0].text().endswith(' · XLL技术笔记'))
            labels = detail.find(css='tag-list')[0].find('a')
            self.assertEqual(len(labels), len(post['tags']) + 1)
            for label in labels[1:]:
                target = page(self.site, label.attrs['href'])
                self.assertIn(route, [anchor.attrs.get('href') for anchor in target.find('a')])
        for route in ['/', '/posts/', '/tags/risc-v/']:
            cards = page(self.site, route).find(css='post-card')
            self.assertEqual(len(cards), len(self.posts))
            self.assertTrue(all(card.find(css='series-tag') for card in cards))
        self.assertEqual(page(self.site, '/series/').find('h1')[0].text(), 'RISC-V OS实验笔记')

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
                        ignore=shutil.ignore_patterns('.git', 'node_modules', 'public', 'resources', '__pycache__', '.hugo_build.lock'))
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
