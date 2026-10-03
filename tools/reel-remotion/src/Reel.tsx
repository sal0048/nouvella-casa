import React from 'react';
import {
  AbsoluteFill, OffthreadVideo, Sequence, interpolate, spring, staticFile,
  useCurrentFrame, useVideoConfig, Easing,
} from 'remotion';

const GOLD = '#C9A84C';
const CREAM = '#F7F3EE';
const NAVY = '#1B2A4A';

const fonts = `
@font-face{font-family:'Cairo';src:url('${staticFile('Cairo-Bold.ttf')}');font-weight:700;}
@font-face{font-family:'Cairo';src:url('${staticFile('Cairo.ttf')}');font-weight:400;}
@font-face{font-family:'Playfair';src:url('${staticFile('Playfair.ttf')}');}
`;

const ease = Easing.bezier(0.22, 1, 0.36, 1);

// One footage shot with a slow camera push and a punch-in on entry
const Shot: React.FC<{from: number; len: number; z0: number; z1: number; ox?: string; oy?: string}> = ({from, len, z0, z1, ox = '50%', oy = '50%'}) => {
  const f = useCurrentFrame();
  const punch = interpolate(f, [0, 6], [1.06, 1], {extrapolateRight: 'clamp', easing: ease});
  const z = interpolate(f, [0, len], [z0, z1]) * punch;
  const blur = interpolate(f, [0, 4], [6, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <OffthreadVideo src={staticFile('table.mp4')} startFrom={Math.round(from * 30)} muted
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${z})`, transformOrigin: `${ox} ${oy}`, filter: `blur(${blur}px)`}} />
    </AbsoluteFill>
  );
};

// Word-by-word Arabic title that rises in
const Title: React.FC<{words: string[]; size: number; color: string; delay?: number; weight?: number}> = ({words, size, color, delay = 0, weight = 700}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{direction: 'rtl', display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: size * 0.25}}>
      {words.map((w, i) => {
        const s = spring({frame: f - delay - i * 4, fps, config: {damping: 14, mass: 0.6}});
        return (
          <span key={i} style={{fontFamily: 'Cairo', fontWeight: weight, fontSize: size, color, lineHeight: 1.25,
            display: 'inline-block', opacity: s, transform: `translateY(${(1 - s) * 50}px)`,
            textShadow: '0 4px 24px rgba(0,0,0,0.45)'}}>{w}</span>
        );
      })}
    </div>
  );
};

const Exit: React.FC<{len: number; children: React.ReactNode}> = ({len, children}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [len - 8, len], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{opacity: o}}>{children}</AbsoluteFill>;
};

const BottomShade: React.FC = () => (
  <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(10,14,25,0.78) 0%, rgba(10,14,25,0.35) 30%, rgba(0,0,0,0) 48%)'}} />
);

// Callout: dot + line drawing + label pill
const Callout: React.FC<{x: number; y: number; dx: number; dy: number; label: string; delay?: number}> = ({x, y, dx, dy, label, delay = 6}) => {
  const f = useCurrentFrame() - delay;
  const {fps} = useVideoConfig();
  const dot = spring({frame: f, fps, config: {damping: 10}});
  const draw = interpolate(f, [4, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
  const pill = spring({frame: f - 16, fps, config: {damping: 13}});
  const len = Math.hypot(dx, dy);
  return (
    <AbsoluteFill>
      <svg width={1080} height={1920} style={{position: 'absolute'}}>
        <circle cx={x} cy={y} r={14 * dot} fill={GOLD} />
        <circle cx={x} cy={y} r={30 * dot} fill="none" stroke={GOLD} strokeWidth={3} opacity={0.6 * dot} />
        <line x1={x} y1={y} x2={x + dx} y2={y + dy} stroke={CREAM} strokeWidth={4}
          strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />
      </svg>
      <div style={{position: 'absolute', left: x + dx, top: y + dy, transform: `translate(-50%,-50%) scale(${pill})`,
        background: 'rgba(247,243,238,0.94)', color: NAVY, fontFamily: 'Cairo', fontWeight: 700, fontSize: 52,
        padding: '10px 40px', borderRadius: 60, direction: 'rtl', whiteSpace: 'nowrap', boxShadow: '0 10px 40px rgba(0,0,0,0.35)'}}>
        {label}
      </div>
    </AbsoluteFill>
  );
};

const Brand: React.FC = () => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 15], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', top: 120, width: '100%', textAlign: 'center', opacity: o}}>
      <div style={{fontFamily: 'Playfair', color: CREAM, fontSize: 40, letterSpacing: 10, textShadow: '0 2px 12px rgba(0,0,0,0.5)'}}>NOUVELLA CASA</div>
      <div style={{width: 90, height: 3, background: GOLD, margin: '14px auto 0'}} />
    </div>
  );
};

const Flash: React.FC = () => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 2, 7], [0, 0.55, 0], {extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{background: CREAM, opacity: o}} />;
};

const EndCard: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const bg = interpolate(f, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
  const logo = spring({frame: f - 6, fps, config: {damping: 16}});
  const line = interpolate(f, [14, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease});
  const btn = spring({frame: f - 30, fps, config: {damping: 11}});
  const pulse = 1 + 0.04 * Math.sin(Math.max(0, f - 45) / 5);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{opacity: bg}}>
        <OffthreadVideo src={staticFile('table.mp4')} startFrom={300} muted
          style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(22px) brightness(0.55)', transform: 'scale(1.15)'}} />
        <AbsoluteFill style={{background: `${NAVY}D9`}} />
      </AbsoluteFill>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column'}}>
        <div style={{fontFamily: 'Playfair', color: CREAM, fontSize: 108, letterSpacing: 8, textAlign: 'center', lineHeight: 1.1,
          opacity: logo, transform: `translateY(${(1 - logo) * 40}px)`}}>NOUVELLA<br />CASA</div>
        <div style={{width: 260 * line, height: 4, background: GOLD, margin: '40px 0 70px'}} />
        <div style={{transform: `scale(${btn * pulse})`, background: GOLD, color: NAVY, fontFamily: 'Cairo', fontWeight: 700,
          fontSize: 76, padding: '18px 80px', borderRadius: 100, direction: 'rtl', boxShadow: '0 16px 50px rgba(0,0,0,0.4)'}}>
          ابعتلنا مساج
        </div>
        <div style={{marginTop: 50}}>
          <Title words={['السعر', 'والألوان،', 'والدفع', 'عند', 'الاستلام']} size={50} color={CREAM} delay={40} weight={400} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Grain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{opacity: 0.07, mixBlendMode: 'overlay', pointerEvents: 'none'}}>
      <svg width="1080" height="1920">
        <filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={f % 12} /></filter>
        <rect width="100%" height="100%" filter="url(#n)" />
      </svg>
    </AbsoluteFill>
  );
};

const Progress: React.FC = () => {
  const f = useCurrentFrame();
  return <div style={{position: 'absolute', top: 0, left: 0, height: 8, width: `${(f / 345) * 100}%`, background: GOLD}} />;
};

export const Reel: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <style>{fonts}</style>

    {/* 1 Hook */}
    <Sequence durationInFrames={80}>
      <Shot from={0} len={80} z0={1.0} z1={1.1} />
      <BottomShade />
      <Exit len={80}>
        <AbsoluteFill style={{justifyContent: 'flex-end', paddingBottom: 330}}>
          <Title words={['طاولة', 'صالون']} size={130} color={CREAM} delay={4} />
          <Title words={['بزوج', 'قواعد', 'خشب']} size={72} color={GOLD} delay={14} />
        </AbsoluteFill>
      </Exit>
    </Sequence>

    {/* 2 Base detail */}
    <Sequence from={80} durationInFrames={85}>
      <Shot from={3.2} len={85} z0={1.35} z1={1.45} oy="78%" />
      <Flash />
      <Exit len={85}><Callout x={560} y={760} dx={0} dy={520} label="خشب مضلّع" /></Exit>
    </Sequence>

    {/* 3 Top detail */}
    <Sequence from={165} durationInFrames={85}>
      <Shot from={6.3} len={85} z0={1.2} z1={1.3} oy="40%" />
      <Flash />
      <Exit len={85}><Callout x={760} y={980} dx={-200} dy={380} label="حواف مدوّرة" /></Exit>
    </Sequence>

    {/* 4 Custom */}
    <Sequence from={250} durationInFrames={95}>
      <Shot from={9.0} len={95} z0={1.12} z1={1.0} />
      <Flash />
      <BottomShade />
      <Exit len={95}>
        <AbsoluteFill style={{justifyContent: 'flex-end', paddingBottom: 330}}>
          <Title words={['على', 'القياس', 'واللون']} size={100} color={CREAM} delay={6} />
          <Title words={['اللي', 'تحب']} size={100} color={GOLD} delay={16} />
        </AbsoluteFill>
      </Exit>
    </Sequence>

    {/* Brand + progress over footage */}
    <Sequence durationInFrames={345}><Brand /><Progress /></Sequence>

    {/* 5 End card */}
    <Sequence from={335} durationInFrames={115}><EndCard /></Sequence>

    <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)'}} />
    <Grain />
  </AbsoluteFill>
);
