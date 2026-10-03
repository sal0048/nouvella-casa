import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'path';
const only = process.argv[2];
const COMP = process.env.COMP || 'NoyaSlide';
const N = Number(process.env.NSLIDES || 8);
const B = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const models = only ? only.split(',') : ['ORION','NUAGE','AXEL','ATLAS','ARC','STELLA'];
const idxs = process.argv[3] ? process.argv[3].split(',').map(Number) : [...Array(N).keys()];
for (const model of models) for (const idx of idxs) {
  const inputProps = {model, idx};
  const composition = await selectComposition({serveUrl, id: COMP, inputProps, browserExecutable: B});
  await renderStill({composition, serveUrl, output: `out/noya/${model}_${idx+1}.png`, inputProps, browserExecutable: B});
  console.log(model, idx+1);
}
