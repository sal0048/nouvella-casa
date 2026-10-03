import soundfile as sf, numpy as np
from kokoro import KPipeline
p = KPipeline(lang_code='f')  # French
for i, line in enumerate(open('lines.txt', encoding='utf-8'), 1):
    st, slot, txt = line.rstrip('\n').split('|')
    audio = np.concatenate([a for _, _, a in p(txt, voice='ff_siwis', speed=1.0)])
    sf.write(f'k{i}.wav', audio, 24000)
    print(i, slot, round(len(audio)/24000, 2), txt)
