import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {REACH} from './noyaReachData';
import {Logo} from './NoyaSlide';

const ESP = '#2A211C';
const SAND = '#F3ECE2';
const CLAY = '#B8925A';
const N = 7;
const f = (n: string) => staticFile(`noya/${n}`);
const fonts = `
@font-face{font-family:'Playfair';src:url('${f('playfair-display-latin-600-normal.woff2')}');font-weight:600;}
@font-face{font-family:'Playfair';src:url('${f('playfair-display-latin-400-italic.woff2')}');font-style:italic;font-weight:400;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-500-normal.woff2')}');font-weight:500;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-600-normal.woff2')}');font-weight:600;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-700-normal.woff2')}');font-weight:700;}
`;
const Photo: React.FC<{k: string; style?: React.CSSProperties}> = ({k, style}) => (
  <Img src={f(`real/${k}.jpg`)} style={{width: '100%', height: '100%', objectFit: 'cover', ...style}} />
);
const Lines: React.FC<{text: string; style: React.CSSProperties}> = ({text, style}) => (
  <div style={style}>{text.split('\n').map((l, i) => <div key={i}>{l}</div>)}</div>
);
const Label: React.FC<{t: string}> = ({t}) => (
  <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 26, letterSpacing: 6, color: CLAY, marginBottom: 26}}>{t}</div>
);

const Chrome: React.FC<{idx: number; dark: boolean}> = ({idx, dark}) => {
  const c = dark ? SAND : ESP;
  return (
    <>
      
      <div style={{position: 'absolute', top: 66, right: 60, fontFamily: 'Mont', fontWeight: 500, fontSize: 24, color: c, opacity: 0.8, letterSpacing: 3}}>
        {String(idx + 1).padStart(2, '0')} / {String(N).padStart(2, '0')}
      </div>
      {idx < N - 1 && (
        <div style={{position: 'absolute', bottom: 54, right: 60, fontFamily: 'Mont', fontWeight: 600, fontSize: 24, letterSpacing: 4, color: c,
          border: `2px solid ${c}`, borderRadius: 40, padding: '10px 26px', display: 'flex', alignItems: 'center', gap: 14}}>GLISSEZ
          <svg width="34" height="16" viewBox="0 0 34 16"><path d="M0 8 H31 M24 1 L32 8 L24 15" fill="none" stroke={c} strokeWidth="2.5" /></svg></div>
      )}
    </>
  );
};

export const NoyaReach: React.FC<{model: string; idx: number}> = ({model, idx}) => {
  const m = REACH.find((x) => x.id === model)!;
  let body: React.ReactNode = null;
  let dark = true;
  if (idx === 0) {
    body = (<>
      <Photo k={m.hero} />
      <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.94) 0%, rgba(28,22,18,0.55) 40%, rgba(0,0,0,0) 65%), linear-gradient(to bottom, rgba(28,22,18,0.6), rgba(0,0,0,0) 22%)'}} />
      <div style={{position: 'absolute', left: 70, right: 70, bottom: 170}}>
        <Lines text={m.hook} style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 70, lineHeight: 1.14, color: SAND}} />
      </div>
    </>);
  } else if (idx === 1) {
    dark = false;
    body = (
      <AbsoluteFill style={{background: SAND, padding: '0 90px', justifyContent: 'center'}}>
        <Label t="ÇA VOUS PARLE ?" />
        <Lines text={m.mirror} style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 72, lineHeight: 1.15, color: ESP}} />
        <div style={{width: 120, height: 4, background: CLAY, margin: '48px 0 36px'}} />
        <div style={{fontFamily: 'Playfair', fontStyle: 'italic', fontSize: 44, color: ESP, opacity: 0.8}}>{m.mirrorSub}</div>
      </AbsoluteFill>
    );
  } else if (idx === 2) {
    body = (
      <AbsoluteFill style={{background: ESP, padding: '0 90px', justifyContent: 'center'}}>
        <div style={{fontFamily: 'Playfair', fontSize: 180, color: CLAY, lineHeight: 0.5, height: 80}}>“</div>
        <Lines text={m.brk} style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 76, lineHeight: 1.18, color: SAND}} />
      </AbsoluteFill>
    );
  } else if (idx === 3) {
    dark = false;
    body = (
      <AbsoluteFill style={{background: SAND}}>
        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 880}}><Photo k={m.reveal} /></div>
        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 200, background: 'linear-gradient(to bottom, rgba(243,236,226,0.95), rgba(243,236,226,0))'}} />
        <div style={{position: 'absolute', top: 880, left: 0, right: 0, bottom: 0, padding: '44px 80px'}}>
          <div style={{fontFamily: 'Playfair', fontStyle: 'italic', fontSize: 44, color: CLAY}}>Voici</div>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 130, letterSpacing: 14, color: ESP, lineHeight: 1}}>{m.id}</div>
          <div style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 32, color: ESP, marginTop: 20, maxWidth: 820, lineHeight: 1.35}}>{m.meaning}</div>
        </div>
      </AbsoluteFill>
    );
  } else if (idx === 4) {
    body = (<>
      <Photo k={m.detail} />
      <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.95) 0%, rgba(28,22,18,0.72) 45%, rgba(28,22,18,0.15) 78%)'}} />
      <div style={{position: 'absolute', left: 80, right: 80, bottom: 170}}>
        <Label t="CE QUI FAIT LA DIFFÉRENCE" />
        {m.details.map((d, i) => (
          <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 28, borderTop: '1px solid rgba(243,236,226,0.25)', padding: '22px 0'}}>
            <span style={{fontFamily: 'Playfair', fontSize: 34, color: CLAY, width: 50}}>{String(i + 1).padStart(2, '0')}</span>
            <span style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 40, color: SAND}}>{d}</span>
          </div>
        ))}
      </div>
    </>);
  } else if (idx === 5) {
    dark = false;
    const g = m.grid;
    body = (
      <AbsoluteFill style={{background: SAND, padding: '160px 60px 170px'}}>
        <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 56, color: ESP, marginBottom: 34, textAlign: 'center'}}>{m.gridTitle}</div>
        <div style={{flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: g.length > 2 ? '1fr 1fr' : '1fr', gridTemplateRows: g.length > 2 ? '1fr 1fr' : '1fr 1fr', gap: 18}}>
          {g.map((k) => <div key={k} style={{borderRadius: 22, overflow: 'hidden', minHeight: 0}}><Photo k={k} /></div>)}
        </div>
      </AbsoluteFill>
    );
  } else {
    body = (
      <AbsoluteFill style={{background: ESP, justifyContent: 'center', alignItems: 'center', padding: '0 90px'}}>
        <div style={{width: 160, height: 3, background: CLAY, margin: '0 0 56px'}} />
        {[['Enregistrez', 'ce post pour votre futur salon'], ['Partagez-le', `à ${m.share}`], ['Écrivez', `« ${m.id} » pour les tissus et les dimensions`]].map(([a, b], i) => (
          <div key={i} style={{display: 'flex', gap: 26, alignItems: 'baseline', marginBottom: 40, width: '100%'}}>
            <span style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 58, color: CLAY, width: 70}}>{i + 1}</span>
            <span style={{fontFamily: 'Mont', fontSize: 40, color: SAND, lineHeight: 1.3}}><b style={{fontWeight: 700}}>{a}</b> {b}</span>
          </div>
        ))}
        <div style={{marginTop: 30, fontFamily: 'Mont', fontWeight: 500, fontSize: 30, color: SAND, opacity: 0.75, letterSpacing: 2}}>Paiement à la livraison · 69 wilayas</div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{background: ESP}}>
      <style>{fonts}</style>
      {body}
      {idx !== N - 1 && <Chrome idx={idx} dark={dark} />}
    </AbsoluteFill>
  );
};
