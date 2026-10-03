import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'path';
const B = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const EDU = {E_ERREURS:5,E_TAILLE:6,E_SECRET:6,E_PETIT:6,B_NOMS:7,E_BOUCLETTE:6,E_QUESTIONS:7,E_HANA_TEST:7,E_QUIZ:5,E_RECEVOIR:6};
const CH = ['C_HANA','C_DROIT_ANGLE','C_TISSUS','C_LAMMA','C_MARBRE_VERRE','C_DAR_MIDA'];
const only = process.argv[2] ? process.argv[2].split(',') : null;
const go = async (id, model, idx, out) => {
  const inputProps = {model, idx};
  const composition = await selectComposition({serveUrl, id, inputProps, browserExecutable: B});
  await renderStill({composition, serveUrl, output: out, inputProps, browserExecutable: B});
};
for (const [m, n] of Object.entries(EDU)) { if (only && !only.includes(m)) continue; for (let i = 0; i < n; i++) await go('NoyaEdu', m, i, `out/w2/${m}_${i+1}.png`); console.log(m); }
for (const m of CH) { if (only && !only.includes(m)) continue; await go('NoyaChoice', m, 0, `out/w2/${m}.png`); console.log(m); }
