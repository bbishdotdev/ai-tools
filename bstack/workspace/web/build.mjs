import { build } from 'esbuild';
import { mkdirSync, writeFileSync, readFileSync, readdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

process.chdir(dirname(fileURLToPath(import.meta.url)));
const assets = resolve('../assets');
mkdirSync(assets, { recursive: true });
const result = await build({
  absWorkingDir: process.cwd(), entryPoints: ['src/main.jsx'], bundle: true, minify: true, outfile: `${assets}/app.js`, metafile: true,
  define: { 'process.env.NODE_ENV': '"production"' }, jsx: 'automatic', target: ['es2022'], legalComments: 'linked',
});
execFileSync('node_modules/.bin/tailwindcss', ['-i', 'src/style.css', '-o', `${assets}/style.css`, '--minify'], { stdio: 'inherit' });
writeFileSync(`${assets}/index.html`, '<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>bstack · Wayfinder</title><link rel="icon" href="data:,"><link rel="stylesheet" href="/style.css"></head><body><div id="root"></div><script type="module" src="/app.js"></script></body></html>\n');
const packages = ['react', 'react-dom', 'scheduler', 'marked', 'dompurify', '@github/markdown-toolbar-element', 'tailwindcss'];
const notices = packages.map(name => {
  const directory = `node_modules/${name}`;
  const metadata = JSON.parse(readFileSync(`${directory}/package.json`, 'utf8'));
  const licenses = readdirSync(directory).filter(file => /^(license|copying)(\.|$)/i.test(file));
  if (!licenses.length) throw new Error(`Missing full license for ${name}`);
  return `${name} ${metadata.version}\n${'='.repeat(name.length + metadata.version.length + 1)}\n${licenses.map(file => readFileSync(`${directory}/${file}`, 'utf8')).join('\n')}\n`;
});
writeFileSync(`${assets}/THIRD_PARTY_NOTICES.txt`, `Third-party software included in Wayfinder browser assets.\n\n${notices.join('\n').trimEnd()}\n`);
const evidence = resolve('../../../.bstack/work/wayfinder-implementation/evidence');
mkdirSync(evidence, { recursive: true });
writeFileSync(`${evidence}/web-bundle-inputs.json`, JSON.stringify(result.metafile, null, 2));
console.log(`Built offline Wayfinder assets in ${assets}`);
