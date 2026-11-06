import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const code = fs.readFileSync(new URL('./cloudfront-directory-index.js', import.meta.url), 'utf8');
const context = vm.createContext({});
vm.runInContext(code, context, {timeout: 1000});

function event(host, uri, querystring = {}) {
  return {request: {method: 'GET', uri, headers: {host: {value: host}}, querystring}};
}

test('apex uses the fixed HTTPS canonical origin before directory rewriting', () => {
  const input = event('xueliangliang.dev', '/');
  const output = context.handler(input);
  assert.equal(output.statusCode, 301);
  assert.equal(output.headers.location.value, 'https://blog.xueliangliang.dev/');
  assert.equal(output.headers['cache-control'].value, 'public, max-age=300');
  assert.equal(input.request.uri, '/');
});

test('apex preserves encoded paths, encoded queries, repeated values and empty flags', () => {
  const output = context.handler(event('XUELIANGLIANG.DEV', '/posts/%E6%B5%8B%E8%AF%95/', {
    q: {value: 'a%20b%26c'},
    tag: {value: 'one', multiValue: [{value: 'one'}, {value: 'a%2Fb'}]},
    flag: {value: ''},
    next: {value: 'https%3A%2F%2Funrelated.example'}
  }));
  assert.equal(output.headers.location.value,
    'https://blog.xueliangliang.dev/posts/%E6%B5%8B%E8%AF%95/?flag=&next=https%3A%2F%2Funrelated.example&q=a%20b%26c&tag=one&tag=a%2Fb');
});

test('apex assets and ads.txt retain their paths', () => {
  for (const uri of ['/ads.txt', '/robots.txt', '/css/site.css', '/series']) {
    const output = context.handler(event('xueliangliang.dev', uri));
    assert.equal(output.headers.location.value, 'https://blog.xueliangliang.dev' + uri);
  }
});

test('blog directory and asset behavior stays unchanged', () => {
  for (const [uri, expected] of [
    ['/', '/index.html'], ['/series', '/series/index.html'],
    ['/series/', '/series/index.html'], ['/posts/why-this-series/', '/posts/why-this-series/index.html'],
    ['/css/site.css', '/css/site.css'], ['/index.xml', '/index.xml'],
    ['/ads.txt', '/ads.txt'], ['/404.html', '/404.html']
  ]) {
    const input = event('blog.xueliangliang.dev', uri, {q: {value: 'keep%20me'}});
    const query = structuredClone(input.request.querystring);
    const output = context.handler(input);
    assert.equal(output, input.request);
    assert.equal(output.uri, expected);
    assert.deepEqual(output.querystring, query);
    assert.equal(output.statusCode, undefined);
  }
});

test('unrelated host does not get redirected and missing optional query is safe', () => {
  const input = event('www.xueliangliang.dev', '/');
  assert.equal(context.handler(input).uri, '/index.html');
  const root = event('xueliangliang.dev', '/');
  delete root.request.querystring;
  assert.equal(context.handler(root).headers.location.value, 'https://blog.xueliangliang.dev/');
});
