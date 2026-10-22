import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { mkdtemp, mkdir, readFile, readdir, rename, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const execute = promisify(execFile);
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export function sourceHash(source) {
  return createHash('sha256').update(source.trim()).digest('hex');
}

// Scan real fenced blocks, not Mermaid examples nested in a longer code fence.
export function diagramSources(markdown) {
  const sources = [];
  let fence = null;
  let body = [];
  for (const line of markdown.split(/\r?\n/)) {
    if (fence === null) {
      const match = line.match(/^ {0,3}(`{3,}|~{3,})\s*(.*?)\s*$/);
      if (match) {
        fence = { marker: match[1][0], length: match[1].length, mermaid: match[2] === 'mermaid' };
        body = [];
      }
      continue;
    }
    const close = line.match(/^ {0,3}(`{3,}|~{3,})\s*$/);
    if (close && close[1][0] === fence.marker && close[1].length >= fence.length) {
      if (fence.mermaid) {
        const source = body.join('\n').trim();
        if (source.length === 0) throw new Error('Empty Mermaid block');
        sources.push(source);
      }
      fence = null;
      body = [];
    } else {
      body.push(line);
    }
  }
  if (fence?.mermaid) throw new Error('Unclosed Mermaid block');
  return sources;
}

async function markdownFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await markdownFiles(path));
    else if (entry.isFile() && path.endsWith('.md')) files.push(path);
  }
  return files.sort();
}

function validateSvg(svg, hash) {
  if (!svg.includes(`<!-- mermaid-source-sha256: ${hash} -->`) ||
      !svg.includes('<svg') || !svg.includes('xmlns="http://www.w3.org/2000/svg"') ||
      /<script\b|\bon\w+\s*=|(?:href|src)="https?:/i.test(svg)) {
    throw new Error(`Invalid or externally dependent diagram ${hash}`);
  }
}

export async function main(args = process.argv.slice(2)) {
  if (args.some(arg => arg !== '--check')) throw new Error('Usage: render-diagrams.mjs [--check]');
  const check = args.includes('--check');
  const diagrams = new Map();
  for (const file of await markdownFiles(join(root, 'content'))) {
    for (const source of diagramSources(await readFile(file, 'utf8'))) {
      diagrams.set(sourceHash(source), source);
    }
  }
  const output = join(root, 'static', 'diagrams');
  await mkdir(output, { recursive: true });
  let scratch;
  try {
    if (!check && diagrams.size) scratch = await mkdtemp(join(tmpdir(), 'blog-mermaid-'));
    for (const [hash, source] of diagrams) {
      const destination = join(output, `${hash}.svg`);
      if (!check) {
        const input = join(scratch, `${hash}.mmd`);
        const svgPath = join(scratch, `${hash}.svg`);
        const config = join(scratch, `${hash}.json`);
        const puppeteerConfig = join(scratch, 'puppeteer.json');
        const browser = {};
        if (process.env.PUPPETEER_EXECUTABLE_PATH) browser.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
        // Opt in only in containers where Chrome's OS sandbox is unavailable.
        if (process.env.MERMAID_NO_SANDBOX === '1') browser.args = ['--no-sandbox'];
        await writeFile(puppeteerConfig, JSON.stringify(browser));
        await writeFile(config, JSON.stringify({
          theme: 'neutral', securityLevel: 'strict', deterministicIds: true,
          deterministicIDSeed: hash, fontFamily: 'sans-serif',
          sequence: { useMaxWidth: true, wrap: true },
          flowchart: { htmlLabels: false },
        }));
        await writeFile(input, source + '\n');
        await execute(join(root, 'node_modules', '.bin', 'mmdc'), [
          '-i', input, '-o', svgPath, '-c', config, '-p', puppeteerConfig,
          '-b', '#ffffff', '--size', '1400', '-q',
        ], { timeout: 120000, maxBuffer: 1024 * 1024 });
        const svg = `<!-- mermaid-source-sha256: ${hash} -->\n${await readFile(svgPath, 'utf8')}`;
        validateSvg(svg, hash);
        // Rename only a completely rendered diagram; preserve old assets on failure.
        const staged = destination + '.new';
        await writeFile(staged, svg);
        await rename(staged, destination);
      }
      validateSvg(await readFile(destination, 'utf8'), hash);
      console.log(`${check ? 'CHECK' : 'RENDER'} ${hash}.svg`);
    }
  } finally {
    if (scratch) await rm(scratch, { recursive: true, force: true });
  }
  // Old committed diagrams are intentionally not deleted automatically.
  console.log(`${diagrams.size} unique Mermaid diagram(s); ${check ? 'all assets verified' : 'render complete'}.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => {
    console.error(error.stderr || error.message);
    process.exitCode = 1;
  });
}
