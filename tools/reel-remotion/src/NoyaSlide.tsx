import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {MODELS, SLIDES} from './noyaData';

const ESP = '#2A211C';
const SAND = '#F3ECE2';
const CLAY = '#B8925A';
const f = (n: string) => staticFile(`noya/${n}`);
const fonts = `
@font-face{font-family:'Playfair';src:url('${f('playfair-display-latin-600-normal.woff2')}');font-weight:600;}
@font-face{font-family:'Playfair';src:url('${f('playfair-display-latin-400-italic.woff2')}');font-style:italic;font-weight:400;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-400-normal.woff2')}');font-weight:400;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-500-normal.woff2')}');font-weight:500;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-600-normal.woff2')}');font-weight:600;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-700-normal.woff2')}');font-weight:700;}
`;

export const Logo: React.FC<{color: string; scale?: number}> = ({color, scale = 1}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: 16 * scale}}>
    <svg width={38 * scale} height={46 * scale} viewBox="0 0 38 46">
      <path d="M3 45 V19 A16 16 0 0 1 35 19 V45" fill="none" stroke={color} strokeWidth="3" />
      <path d="M12 45 V24 A7 7 0 0 1 26 24 V45" fill="none" stroke={CLAY} strokeWidth="3" />
    </svg>
    <div style={{lineHeight: 1}}>
      <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 34 * scale, letterSpacing: 8 * scale, color}}>NOYA</div>
      <div style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 13 * scale, letterSpacing: 9.5 * scale, color: CLAY, marginTop: 4 * scale}}>HOME</div>
    </div>
  </div>
);

const Chrome: React.FC<{idx: number; dark: boolean}> = ({idx, dark}) => {
  const c = dark ? SAND : ESP;
  return (
    <>
      
      <div style={{position: 'absolute', top: 66, right: 60, fontFamily: 'Mont', fontWeight: 500, fontSize: 24, color: c, opacity: 0.8, letterSpacing: 3}}>
        {String(idx + 1).padStart(2, '0')} / {String(SLIDES).padStart(2, '0')}
      </div>
      {idx < SLIDES - 1 && (
        <div style={{position: 'absolute', bottom: 54, right: 60, fontFamily: 'Mont', fontWeight: 600, fontSize: 24, letterSpacing: 4, color: c,
          border: `2px solid ${c}`, borderRadius: 40, padding: '10px 26px', opacity: 0.9, display: 'flex', alignItems: 'center', gap: 14}}>GLISSEZ
          <svg width="34" height="16" viewBox="0 0 34 16"><path d="M0 8 H31 M24 1 L32 8 L24 15" fill="none" stroke={c} strokeWidth="2.5" /></svg></div>
      )}
    </>
  );
};

const Photo: React.FC<{src: string; style?: React.CSSProperties}> = ({src, style}) => (
  <Img src={f(src)} style={{width: '100%', height: '100%', objectFit: 'cover', ...style}} />
);

const Lines: React.FC<{text: string; style: React.CSSProperties}> = ({text, style}) => (
  <div style={style}>{text.split('\n').map((l, i) => <div key={i}>{l}</div>)}</div>
);

export const NoyaSlide: React.FC<{model: string; idx: number}> = ({model, idx}) => {
  const m = MODELS.find((x) => x.id === model)!;
  const sib = MODELS.find((x) => x.id === m.sibling)!;
  const isFirstOfPair = MODELS.indexOf(m) % 2 === 0;
  if (idx === 99) {
    // "Duel" post: the two siblings side by side, comments decide
    const half = (mm: typeof m, label: string) => (
      <div style={{position: 'relative', flex: 1, overflow: 'hidden'}}>
        <Photo src={mm.img} />
        <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.9), rgba(0,0,0,0) 45%)'}} />
        <div style={{position: 'absolute', bottom: 150, width: '100%', textAlign: 'center'}}>
          <div style={{fontFamily: 'Mont', fontWeight: 700, fontSize: 30, color: CLAY, letterSpacing: 6}}>{label}</div>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 70, color: SAND, letterSpacing: 6}}>{mm.id}</div>
        </div>
      </div>
    );
    return (
      <AbsoluteFill style={{background: ESP}}>
        <style>{fonts}</style>
        <div style={{display: 'flex', height: '100%', gap: 6}}>{half(m, 'TEAM 1')}{half(sib, 'TEAM 2')}</div>
        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 330, background: 'linear-gradient(to bottom, rgba(28,22,18,0.92), rgba(0,0,0,0))'}} />
        
        <div style={{position: 'absolute', top: 150, width: '100%', textAlign: 'center', fontFamily: 'Playfair', fontWeight: 600, fontSize: 64, color: SAND}}>Vous choisissez laquelle ?</div>
        <div style={{position: 'absolute', top: 560, left: '50%', transform: 'translateX(-50%)', width: 150, height: 150, borderRadius: 100, background: CLAY,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Playfair', fontWeight: 600, fontSize: 56, color: ESP}}>ou</div>
        <div style={{position: 'absolute', bottom: 56, width: '100%', textAlign: 'center', fontFamily: 'Mont', fontWeight: 600, fontSize: 32, color: SAND}}>Répondez 1 ou 2 en commentaire</div>
      </AbsoluteFill>
    );
  }
  let body: React.ReactNode = null;
  let dark = true;

  if (idx === 0) {
    body = (
      <>
        <Photo src={m.img} />
        <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.92) 0%, rgba(28,22,18,0.55) 38%, rgba(0,0,0,0) 62%), linear-gradient(to bottom, rgba(28,22,18,0.55), rgba(0,0,0,0) 22%)'}} />
        <div style={{position: 'absolute', left: 70, right: 70, bottom: 170}}>
          <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 24, letterSpacing: 6, color: CLAY, marginBottom: 22}}>{m.family.toUpperCase()}</div>
          <Lines text={m.hook} style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 72, lineHeight: 1.12, color: SAND}} />
        </div>
      </>
    );
  } else if (idx === 1) {
    dark = false;
    body = (
      <AbsoluteFill style={{background: SAND, padding: '0 90px', justifyContent: 'center'}}>
        <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 26, letterSpacing: 6, color: CLAY, marginBottom: 30}}>VOUS RECONNAISSEZ VOTRE SALON ?</div>
        <div style={{fontFamily: 'Playfair', fontSize: 200, color: CLAY, lineHeight: 0.6, height: 90}}>“</div>
        <Lines text={m.problem} style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 70, lineHeight: 1.15, color: ESP}} />
        <div style={{width: 120, height: 4, background: CLAY, margin: '48px 0 36px'}} />
        <div style={{fontFamily: 'Playfair', fontStyle: 'italic', fontSize: 40, color: ESP, opacity: 0.8}}>{m.problemSub}</div>
      </AbsoluteFill>
    );
  } else if (idx === 2) {
    dark = false;
    body = (
      <AbsoluteFill style={{background: SAND}}>
        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 900}}><Photo src={m.img} /></div>
        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 200, background: 'linear-gradient(to bottom, rgba(243,236,226,0.95), rgba(243,236,226,0))'}} />
        <div style={{position: 'absolute', top: 900, left: 0, right: 0, bottom: 0, padding: '46px 80px'}}>
          <div style={{fontFamily: 'Playfair', fontStyle: 'italic', fontSize: 44, color: CLAY}}>Voici</div>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 132, letterSpacing: 14, color: ESP, lineHeight: 1}}>{m.id}</div>
          <div style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 32, color: ESP, marginTop: 22, maxWidth: 760, lineHeight: 1.35}}>{m.tagline}</div>
        </div>
      </AbsoluteFill>
    );
  } else if (idx === 3) {
    body = (
      <>
        <Photo src={m.img} style={{transform: 'scale(1.35)', transformOrigin: '50% 60%'}} />
        <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.94) 0%, rgba(28,22,18,0.7) 45%, rgba(28,22,18,0.15) 75%)'}} />
        <div style={{position: 'absolute', left: 80, right: 80, bottom: 170}}>
          <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 26, letterSpacing: 6, color: CLAY, marginBottom: 30}}>LES DÉTAILS</div>
          {m.details.map((d, i) => (
            <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 28, borderTop: '1px solid rgba(243,236,226,0.25)', padding: '22px 0'}}>
              <span style={{fontFamily: 'Playfair', fontSize: 34, color: CLAY, width: 50}}>{String(i + 1).padStart(2, '0')}</span>
              <span style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 40, color: SAND}}>{d}</span>
            </div>
          ))}
        </div>
      </>
    );
  } else if (idx === 4) {
    body = (
      <AbsoluteFill style={{background: ESP, padding: '0 90px', justifyContent: 'center'}}>
        <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 26, letterSpacing: 6, color: CLAY, marginBottom: 20}}>POURQUOI {m.id}</div>
        <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 66, color: SAND, lineHeight: 1.15, marginBottom: 50}}>Ce qui la rend différente</div>
        {m.why.map((w, i) => (
          <div key={i} style={{display: 'flex', gap: 34, alignItems: 'flex-start', marginBottom: 44}}>
            <span style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 64, color: CLAY, lineHeight: 1, width: 90}}>{String(i + 1).padStart(2, '0')}</span>
            <span style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 40, color: SAND, lineHeight: 1.35}}>{w}</span>
          </div>
        ))}
      </AbsoluteFill>
    );
  } else if (idx === 5) {
    dark = false;
    body = (
      <AbsoluteFill style={{background: SAND, padding: '0 80px', justifyContent: 'center'}}>
        <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 26, letterSpacing: 6, color: CLAY, marginBottom: 20}}>VOS QUESTIONS</div>
        <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 66, color: ESP, marginBottom: 46}}>On vous répond.</div>
        {m.faq.map(([q, a], i) => (
          <div key={i} style={{background: '#fff', borderRadius: 28, padding: '38px 44px', marginBottom: 30, boxShadow: '0 10px 40px rgba(42,33,28,0.08)', borderLeft: `8px solid ${CLAY}`}}>
            <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 44, color: ESP, marginBottom: 14}}>{q}</div>
            <div style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 36, color: ESP, opacity: 0.8, lineHeight: 1.35}}>{a}</div>
          </div>
        ))}
      </AbsoluteFill>
    );
  } else if (idx === 6) {
    body = (
      <>
        <Photo src={sib.img} style={{filter: isFirstOfPair ? 'blur(14px) brightness(0.55)' : 'brightness(0.6)', transform: 'scale(1.08)'}} />
        <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(28,22,18,0.25), rgba(28,22,18,0.85))', justifyContent: 'center', alignItems: 'center', padding: '0 90px'}}>
          <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 26, letterSpacing: 6, color: CLAY, marginBottom: 28}}>{isFirstOfPair ? 'À SUIVRE' : 'LA MÊME FAMILLE'}</div>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 84, color: SAND, textAlign: 'center', lineHeight: 1.1}}>{m.teaser}</div>
          <div style={{width: 120, height: 4, background: CLAY, margin: '44px 0'}} />
          <Lines text={m.teaserSub} style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 38, color: SAND, textAlign: 'center', lineHeight: 1.45}} />
        </AbsoluteFill>
      </>
    );
  } else {
    body = (
      <AbsoluteFill style={{background: ESP, justifyContent: 'center', alignItems: 'center', padding: '0 90px'}}>
        <div style={{width: 160, height: 3, background: CLAY, margin: '0 0 56px'}} />
        <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 58, color: SAND, textAlign: 'center', lineHeight: 1.2, marginBottom: 44}}>
          Envie de {m.id} chez vous ?
        </div>
        <div style={{background: CLAY, color: ESP, fontFamily: 'Mont', fontWeight: 700, fontSize: 44, padding: '26px 60px', borderRadius: 80, marginBottom: 60}}>
          Écrivez « {m.id} » en message
        </div>
        {[['Paiement', 'à la livraison'], ['Livraison', 'dans les 69 wilayas'], ['Fabriquée', `sur commande en ${m.delay}`], ['Au choix', m.finishes.toLowerCase()]].map(([a, b], i) => (
          <div key={i} style={{fontFamily: 'Mont', fontSize: 36, color: SAND, marginBottom: 18}}>
            <span style={{fontWeight: 700, color: CLAY}}>{a}</span> <span style={{fontWeight: 400}}>{b}</span>
          </div>
        ))}
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{background: ESP}}>
      <style>{fonts}</style>
      {body}
      {idx !== SLIDES - 1 && <Chrome idx={idx} dark={dark} />}
    </AbsoluteFill>
  );
};
