import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

const GOLD = '#C9A84C';
const CREAM = '#F7F3EE';
const NAVY = '#1B2A4A';
const fonts = `
@font-face{font-family:'Cairo';src:url('${staticFile('Cairo-Bold.ttf')}');font-weight:700;}
@font-face{font-family:'Montserrat';src:url('${staticFile('montserrat-latin-700-normal.woff2')}');font-weight:700;}
@font-face{font-family:'Montserrat';src:url('${staticFile('montserrat-latin-600-normal.woff2')}');font-weight:600;}
@font-face{font-family:'Playfair';src:url('${staticFile('Playfair.ttf')}');}
`;

// French captions; timings follow the original Arabic captions (seconds)
const LINES: [number, number, string][] = [
  [0.2, 3.95, 'Envie d’une table basse qui dure ?'],
  [4.0, 6.35, 'Regardez de plus près'],
  [6.4, 8.15, 'Plateau en porcelaine'],
  [8.2, 10.35, 'Base 100 % bois de hêtre'],
  [10.4, 12.45, 'Couleurs au choix, sur commande'],
  [12.5, 14.15, 'Plusieurs formes disponibles'],
  [14.2, 17.15, 'Livraison dans les 69 wilayas'],
  [17.2, 18.6, 'Bienvenue à tous !'],
];
const FPS = 30;
export const FR_DURATION = Math.round(37.85 * FPS);
const BOX_START = 0.15, BOX_END = 18.7;

const Line: React.FC<{text: string; len: number}> = ({text, len}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 14, mass: 0.6}});
  const out = interpolate(f, [len - 4, len], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{fontFamily: 'Montserrat', fontWeight: 700, fontSize: 52, letterSpacing: 0.5, color: CREAM, textAlign: 'center',
      opacity: s * out, transform: `translateY(${(1 - s) * 24}px)`}}>{text}</div>
  );
};

// Opaque caption bar that hides the burned-in Arabic subtitles (source band y≈915–985 of 1280)
const CaptionBar: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const len = Math.round((BOX_END - BOX_START) * fps);
  const inS = spring({frame: f, fps, config: {damping: 16}});
  const out = interpolate(f, [len - 6, len], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: 50, right: 50, top: 1340, height: 170, borderRadius: 28,
      background: 'rgba(27,42,74,0.97)', borderBottom: `5px solid ${GOLD}`, boxShadow: '0 18px 50px rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: out,
      transform: `scaleX(${inS})`}}>
      {LINES.map(([a, b, t], i) => (
        <Sequence key={i} from={Math.round((a - BOX_START) * fps)} durationInFrames={Math.round((b - a) * fps)} layout="none">
          <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <Line text={t} len={Math.round((b - a) * fps)} />
          </div>
        </Sequence>
      ))}
    </div>
  );
};

const EndCta: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f, fps, config: {damping: 13}});
  const pulse = 1 + 0.035 * Math.sin(Math.max(0, f - 20) / 5);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 300}}>
      <div style={{transform: `scale(${s * pulse})`, background: GOLD, color: NAVY, fontFamily: 'Montserrat', fontWeight: 700,
        fontSize: 64, padding: '16px 64px', borderRadius: 90, boxShadow: '0 16px 50px rgba(0,0,0,0.4)'}}>Écrivez-nous en message</div>
      <div style={{marginTop: 26, opacity: s, fontFamily: 'Montserrat', fontWeight: 700, fontSize: 44, color: CREAM,
        background: 'rgba(27,42,74,0.85)', padding: '8px 36px', borderRadius: 40}}>Paiement à la livraison</div>
    </AbsoluteFill>
  );
};

export const FrReel: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <style>{fonts}</style>
    <OffthreadVideo src={staticFile('fr.mp4')} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    <Sequence from={Math.round(BOX_START * FPS)} durationInFrames={Math.round((BOX_END - BOX_START) * FPS)}><CaptionBar /></Sequence>
    <Sequence from={FR_DURATION - 120}><EndCta /></Sequence>
  </AbsoluteFill>
);
