import assert from 'node:assert/strict';
import test from 'node:test';
import { diagramSources, sourceHash } from './render-diagrams.mjs';

test('extract Mermaid fences and normalize Hugo code-block whitespace', () => {
  const source = 'sequenceDiagram\nA->>B: hello';
  assert.deepEqual(diagramSources('```mermaid\n' + source + '\n```\n'), [source]);
  assert.equal(sourceHash('\n' + source + '\n'), sourceHash(source));
  assert.equal(sourceHash('hello'), '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
});

test('ignore other languages and examples inside a longer fence', () => {
  const document = '````markdown\n```mermaid\nflowchart LR\nA-->B\n```\n````\n';
  assert.deepEqual(diagramSources(document), []);
  assert.deepEqual(diagramSources('```sh\necho mermaid\n```\n'), []);
});

test('support tilde fences, CRLF and multiple diagrams', () => {
  assert.deepEqual(diagramSources('~~~mermaid\r\nflowchart LR\r\nA-->B\r\n~~~\r\n```mermaid\nx\n```'), ['flowchart LR\nA-->B', 'x']);
});

test('reject blank or unterminated diagrams', () => {
  assert.throws(() => diagramSources('```mermaid\n\n```'), /Empty/);
  assert.throws(() => diagramSources('```mermaid\nx'), /Unclosed/);
});
