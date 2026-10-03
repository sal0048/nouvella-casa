import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {EDU, CHOICES} from './noyaEduData';

const ESP = '#2A211C';
const SAND = '#F3ECE2';
const CLAY = '#B8925A';
const f = (n: string) => staticFile(`noya/${n}`);
const fonts = `
@font-face{font-family:'Playfair';src:url('${f('playfair-display-latin-600-normal.woff2')}');font-weight:600;}
@font-face{font-family:'Playfair';src:url('${f('playfair-display-latin-400-italic.woff2')}');font-style:italic;font-weight:400;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-500-normal.woff2')}');font-weight:500;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-600-normal.woff2')}');font-weight:600;}
@font-face{font-family:'Mont';src:url('${f('montserrat-latin-700-normal.woff2')}');font-weight:700;}
`;
const Photo: React.FC<{k: string; style?: React.CSSProperties}> = ({k, style}) => (
  <Img src={f(`${k}.jpg`)} style={{width: '100%', height: '100%', objectFit: 'cover', ...style}} />
);
const Lines: React.FC<{text: string; style: React.CSSProperties}> = ({text, style}) => (
  <div style={style}>{text.split('\n').map((l, i) => <div key={i}>{l}</div>)}</div>
);
const Swipe: React.FC<{c: string}> = ({c}) => (
  <div style={{position: 'absolute', bottom: 54, right: 60, fontFamily: 'Mont', fontWeight: 600, fontSize: 24, letterSpacing: 4, color: c,
    border: `2px solid ${c}`, borderRadius: 40, padding: '10px 26px', display: 'flex', alignItems: 'center', gap: 14}}>GLISSEZ
    <svg width="34" height="16" viewBox="0 0 34 16"><path d="M0 8 H31 M24 1 L32 8 L24 15" fill="none" stroke={c} strokeWidth="2.5" /></svg></div>
);
const Count: React.FC<{i: number; n: number; c: string}> = ({i, n, c}) => (
  <div style={{position: 'absolute', top: 66, right: 60, fontFamily: 'Mont', fontWeight: 500, fontSize: 24, color: c, opacity: 0.8, letterSpacing: 3}}>
    {String(i + 1).padStart(2, '0')} / {String(n).padStart(2, '0')}
  </div>
);

export const eduSlides = (id: string) => EDU.find((e) => e.id === id)!.points.length + 2;

export const NoyaEdu: React.FC<{model: string; idx: number}> = ({model, idx}) => {
  const e = EDU.find((x) => x.id === model)!;
  const n = e.points.length + 2;
  let body: React.ReactNode;
  let dark = true;
  if (idx === 0) {
    body = (<>
      <Photo k={e.cover} />
      <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.94) 0%, rgba(28,22,18,0.55) 42%, rgba(0,0,0,0) 68%)'}} />
      <div style={{position: 'absolute', left: 70, right: 70, bottom: 170}}>
        <div style={{fontFamily: 'Mont', fontWeight: 600, fontSize: 26, letterSpacing: 6, color: CLAY, marginBottom: 22}}>{e.label}</div>
        <Lines text={e.title} style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 80, lineHeight: 1.1, color: SAND}} />
      </div>
    </>);
  } else if (idx === n - 1) {
    body = (
      <AbsoluteFill style={{background: ESP, justifyContent: 'center', padding: '0 90px'}}>
        <div style={{width: 120, height: 4, background: CLAY, marginBottom: 50}} />
        <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 66, color: SAND, lineHeight: 1.2, marginBottom: 60}}>{e.end}</div>
        {['Enregistrez ce post', 'Partagez-le à un proche', 'Écrivez-nous en message'].map((t, i) => (
          <div key={i} style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 38, color: SAND, marginBottom: 22}}>
            <span style={{fontFamily: 'Playfair', fontWeight: 600, color: CLAY, marginRight: 24}}>{i + 1}</span>{t}</div>
        ))}
        <div style={{marginTop: 40, fontFamily: 'Mont', fontWeight: 500, fontSize: 28, color: SAND, opacity: 0.7, letterSpacing: 2}}>Noya Home · Paiement à la livraison · 69 wilayas</div>
      </AbsoluteFill>
    );
  } else {
    const p = e.points[idx - 1];
    const num = String(idx).padStart(2, '0');
    if (p.img) {
      body = (<>
        <Photo k={p.img} />
        <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.95) 0%, rgba(28,22,18,0.7) 45%, rgba(28,22,18,0.1) 80%)'}} />
        <div style={{position: 'absolute', left: 80, right: 80, bottom: 170}}>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 90, color: CLAY, lineHeight: 1}}>{num}</div>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 64, color: SAND, lineHeight: 1.15, marginTop: 16}}>{p.h}</div>
          {p.t && <div style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 38, color: SAND, opacity: 0.9, lineHeight: 1.4, marginTop: 24}}>{p.t}</div>}
        </div>
      </>);
    } else {
      dark = false;
      body = (
        <AbsoluteFill style={{background: SAND, justifyContent: 'center', padding: '0 90px'}}>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 140, color: CLAY, lineHeight: 1}}>{num}</div>
          <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 72, color: ESP, lineHeight: 1.15, marginTop: 20}}>{p.h}</div>
          {p.t && <div style={{fontFamily: 'Mont', fontWeight: 500, fontSize: 40, color: ESP, opacity: 0.8, lineHeight: 1.4, marginTop: 30}}>{p.t}</div>}
        </AbsoluteFill>
      );
    }
  }
  return (
    <AbsoluteFill style={{background: ESP}}>
      <style>{fonts}</style>
      {body}
      {idx !== n - 1 && <><Count i={idx} n={n} c={dark ? SAND : ESP} /><Swipe c={dark ? SAND : ESP} /></>}
    </AbsoluteFill>
  );
};

export const NoyaChoice: React.FC<{model: string}> = ({model}) => {
  const c = CHOICES.find((x) => x.id === model)!;
  const k = c.items.length;
  const cols = k === 4 ? 2 : k;
  return (
    <AbsoluteFill style={{background: SAND, padding: '70px 50px 60px'}}>
      <style>{fonts}</style>
      <div style={{fontFamily: 'Playfair', fontWeight: 600, fontSize: 64, color: ESP, textAlign: 'center', lineHeight: 1.15, marginBottom: 40}}>{c.title}</div>
      <div style={{flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gridAutoRows: '1fr', gap: 18}}>
        {c.items.map((it) => (
          <div key={it.l} style={{position: 'relative', borderRadius: 26, overflow: 'hidden', minHeight: 0}}>
            <Photo k={it.img} />
            <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(28,22,18,0.85), rgba(0,0,0,0) 45%)'}} />
            <div style={{position: 'absolute', top: 22, left: 22, width: 86, height: 86, borderRadius: 50, background: CLAY, color: ESP,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Playfair', fontWeight: 600, fontSize: 52}}>{it.l}</div>
            <div style={{position: 'absolute', bottom: 26, width: '100%', textAlign: 'center', fontFamily: 'Mont', fontWeight: 700, fontSize: k > 2 ? 36 : 40, color: SAND, letterSpacing: 2}}>{it.name}</div>
          </div>
        ))}
      </div>
      <div style={{marginTop: 36, textAlign: 'center', fontFamily: 'Mont', fontWeight: 600, fontSize: 34, color: ESP}}>{c.foot}</div>
    </AbsoluteFill>
  );
};
