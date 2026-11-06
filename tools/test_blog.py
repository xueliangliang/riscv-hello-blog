#!/usr/bin/env python3
"""Exercise authoring and publication state transitions in disposable real sites."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

import blog
from test_site import page

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='blog-workflow-', dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'source'
        shutil.copytree(ROOT, self.root,
                        ignore=shutil.ignore_patterns('.git', 'node_modules', 'public', 'build', 'resources', '__pycache__', '.hugo_build.lock'))
        with (self.root / 'data/series.toml').open('a') as output:
            output.write('\n[workflow]\ntitle="工作流测试系列"\npage="/workflow-course"\n'
                         '[[workflow.parts]]\nid="next"\nfirst=0\nlast=0\n'
                         '[workflow.planned]\n"0"="待写的文章"\n')
        overview = self.root / 'content/workflow-course/_index.md'
        overview.parent.mkdir()
        overview.write_text('+++\ntitle="工作流测试系列"\ntype="series"\nseries_id="workflow"\n+++\n{{< series-part id="next" >}}\n')

    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(self.root / 'tools/blog.py'), *args],
                                cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout)
        return result

    def new_chapter(self):
        self.cli('new', 'workflow-next', '--title', '自动化下一篇', '--description', '用于隔离验证的真实文章',
                 '--series', 'workflow', '--order', '0', '--tags', 'workflowtopic')
        return self.root / 'content/posts/00-workflow-next.md'

    def row(self, site, number):
        return next(node for node in page(site, '/workflow-course/').find('li') if node.attrs.get('data-order') == str(number))

    def test_actual_cli_draft_build_excludes_article_from_all_public_lists(self):
        post = self.new_chapter()
        self.assertTrue(blog.read_post(post)['meta']['draft'])
        self.assertFalse(blog.read_post(post)['meta']['series_confirmed'])
        self.cli('validate')
        self.cli('build')
        site = Path(self.cli('artifact').stdout.strip())
        self.assertFalse((site / 'posts/workflow-next').exists())
        self.assertFalse((site / 'tags/workflowtopic').exists())
        self.assertNotIn('workflow-next', (site / 'index.xml').read_text())
        self.assertNotIn('workflow-next', (site / 'sitemap.xml').read_text())
        self.assertNotIn('/posts/workflow-next/', [anchor.attrs.get('href') for anchor in page(site, '/').find('a')])
        self.assertEqual(self.row(site, 0).attrs['data-status'], 'planned')
        self.assertFalse(self.row(site, 0).find('a'))
        before = post.read_bytes()
        self.cli('confirm', 'workflow-next', success=False)
        self.assertEqual(post.read_bytes(), before)

    def test_pending_live_mismatch_confirmation_and_second_build(self):
        post = self.new_chapter()
        blog.atomic_text(post, post.read_text().replace('draft = true', 'draft = false'))
        initial = blog.build_site(self.root)
        site = Path(initial['site'])
        self.assertEqual(self.row(site, 0).attrs['data-status'], 'pending')
        self.assertIn('00. 自动化下一篇', self.row(site, 0).text())
        self.assertEqual(self.row(site, 0).find('a')[0].attrs['href'], '/posts/workflow-next/')
        self.assertEqual(page(site, '/').find(css='post-card')[0].find('h3')[0].find('a')[0].attrs['href'], '/posts/workflow-next/')
        self.assertEqual(len(page(site, '/tags/workflowtopic/').find(css='post-card')), 1)
        self.assertIn('/posts/workflow-next/', (site / 'index.xml').read_text())
        self.assertIn('/posts/workflow-next/', (site / 'sitemap.xml').read_text())
        self.confirm_against_local_server(post)

    def confirm_against_local_server(self, post):
        class Handler(SimpleHTTPRequestHandler):
            document_root = self.root
            requests = 0

            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(self.document_root), **kwargs)

            def log_message(self, format, *args):
                pass

            def do_GET(self):
                type(self).requests += 1
                super().do_GET()

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        config = self.root / 'hugo.toml'
        config.write_text(config.read_text().replace('https://blog.xueliangliang.dev/', f'http://127.0.0.1:{server.server_port}/'))
        first = blog.build_site(self.root)
        Handler.document_root = Path(first['site'])
        original = (Handler.document_root / 'posts/workflow-next/index.html').read_bytes()
        source = post.read_text()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            post.write_text(source + '\nThis content is not online yet.\n')
            with self.assertRaisesRegex(ValueError, 'Live article'):
                blog.confirm('workflow-next', self.root, allow_loopback=True)
            self.assertFalse(blog.read_post(post)['meta']['series_confirmed'])
            post.write_text(source)
            blog.confirm('workflow-next', self.root, allow_loopback=True)
            self.assertTrue(blog.read_post(post)['meta']['series_confirmed'])
            self.assertGreaterEqual(Handler.requests, 2)
            with self.assertRaisesRegex(ValueError, 'stale'):
                blog.artifact(self.root)
            second = blog.build_site(self.root)
            confirmed_site = Path(second['site'])
            self.assertEqual(self.row(confirmed_site, 0).attrs['data-status'], 'confirmed')
            self.assertEqual((confirmed_site / 'posts/workflow-next/index.html').read_bytes(), original)
            receipt = json.loads((self.root / 'build/confirmations/workflow-next.json').read_text())
            self.assertTrue(receipt['url'].endswith('/posts/workflow-next/'))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


    def test_failed_build_cannot_reuse_old_success_and_artifact_detects_tampering(self):
        receipt = blog.build_site(self.root)
        self.assertEqual(blog.artifact(self.root), Path(receipt['site']))
        (Path(receipt['site']) / 'index.html').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'modified'):
            blog.artifact(self.root)
        blog.build_site(self.root)
        (self.root / 'content/posts/duplicate.md').write_text(
            '+++\ntitle="Duplicate"\nslug="why-this-series"\ndate=2020-01-01T00:00:00+08:00\ndraft=true\n+++\n')
        with self.assertRaisesRegex(ValueError, 'duplicate slug'):
            blog.build_site(self.root)
        self.assertEqual(json.loads((self.root / 'build/latest.json').read_text())['status'], 'FAIL')
        with self.assertRaisesRegex(ValueError, 'No successful current build'):
            blog.artifact(self.root)

    def test_new_refuses_duplicates_bad_slugs_and_orders_without_overwriting(self):
        post = self.new_chapter()
        before = post.read_bytes()
        self.cli('new', 'workflow-next', '--title', 'Do not replace', success=False)
        self.assertEqual(post.read_bytes(), before)
        for args in [('new', '../escape', '--title', 'Invalid'),
                     ('new', 'duplicate-order', '--title', 'Invalid', '--series', 'workflow', '--order', '0'),
                     ('new', 'unknown-series', '--title', 'Invalid', '--series', 'missing'),
                     ('new', 'missing-order', '--title', 'Invalid', '--series', 'riscv-os')]:
            self.cli(*args, success=False)
        self.assertEqual(post.read_bytes(), before)

    def test_successful_but_empty_hugo_is_not_a_successful_build(self):
        directory = Path(self.temporary.name) / 'fake-bin'
        directory.mkdir()
        fake = directory / 'hugo'
        fake.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do\n if [ "$1" = "--destination" ]; then mkdir -p "$2"; break; fi\n shift\ndone\nexit 0\n')
        fake.chmod(0o755)
        before = os.environ.get('PATH', '')
        try:
            os.environ['PATH'] = str(directory) + os.pathsep + before
            with self.assertRaisesRegex(ValueError, 'required output'):
                blog.build_site(self.root)
        finally:
            os.environ['PATH'] = before
        self.assertEqual(json.loads((self.root / 'build/latest.json').read_text())['status'], 'FAIL')

    def test_current_roadmap_has_exactly_one_row_per_configured_order(self):
        site = Path(blog.build_site(self.root)['site'])
        rows = [node for node in page(site, '/series/').find('li') if 'data-order' in node.attrs]
        parts = blog.registry(self.root)['riscv-os']['parts']
        expected = [number for part in parts for number in range(part['first'], part['last'] + 1)]
        posts = [post['meta'] for post in blog.validate(self.root) if post['meta'].get('series_id') == 'riscv-os']
        visible = [post for post in posts if not post.get('draft', False) and post['date'] <= blog.datetime.now().astimezone()]
        confirmed = sorted(post['series_order'] for post in visible if post.get('series_confirmed'))
        planned = sorted(set(expected) - {post['series_order'] for post in visible})
        self.assertEqual([int(row.attrs['data-order']) for row in rows], expected)
        self.assertEqual([int(row.attrs['data-order']) for row in rows if row.attrs['data-status'] == 'confirmed'], confirmed)
        self.assertEqual([int(row.attrs['data-order']) for row in rows if row.attrs['data-status'] == 'planned'], planned)

    def test_mixed_case_tags_need_canonical_titles_and_rebuild_deterministically(self):
        term = self.root / 'content/tags/virtio/_index.md'
        original = term.read_text()
        term.unlink()
        with self.assertRaisesRegex(ValueError, 'canonical term title'):
            blog.validate(self.root)
        term.write_text(original)
        first = blog.build_site(self.root)
        second = blog.build_site(self.root)
        self.assertEqual(first['files'], second['files'])
        self.assertEqual(page(Path(second['site']), '/tags/virtio/').find('h1')[0].text(), 'VirtIO')

    def test_new_standalone_and_second_series_automatically_join_their_lists(self):
        with (self.root / 'data/series.toml').open('a') as output:
            output.write('\n[other]\ntitle="第二个系列"\npage="/other"\ncode_repository_url=""\n')
        overview = self.root / 'content/other/_index.md'
        overview.parent.mkdir()
        overview.write_text('+++\ntitle="第二个系列"\ntype="series"\nseries_id="other"\n+++\n')
        for slug, extra in [('standalone-note', []), ('other-note', ['--series', 'other'])]:
            self.cli('new', slug, '--title', slug, '--description', 'A test note', '--tags', 'workflowtopic', *extra)
            path = self.root / 'content/posts' / (slug + '.md')
            path.write_text(path.read_text().replace('draft = true', 'draft = false'))
        site = Path(blog.build_site(self.root)['site'])
        self.assertFalse(page(site, '/posts/standalone-note/').find(css='series-tag'))
        self.assertEqual(len(page(site, '/other/').find(css='post-card')), 1)
        self.assertEqual(len(page(site, '/tags/workflowtopic/').find(css='post-card')), 2)


if __name__ == '__main__':
    unittest.main()
