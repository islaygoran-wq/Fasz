#!/usr/bin/env python3
"""Magyar felolvasás (Piper TTS) a videó feliratai alapján.

  python3 narrate.py synth <voice.onnx>   # feliratonként WAV + narration_timing.js
  python3 narrate.py mix                  # out/captions.json alapján hangsáv + MP4 összefűzés
"""
import json, os, re, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(HERE, 'out', 'clips')
OUT = os.path.join(HERE, 'out')

# Kiejtés: latin/szaknyelvi szavak magyaros átírása a TTS számára
STEMS = [
    ('mucoperiostealis', 'mukoperioszteális'), ('periosteum', 'perioszteum'),
    ('buccalis', 'bukkális'), ('distalis', 'disztális'), ('mesialis', 'meziális'),
    ('lingualis', 'lingvális'), ('medialis', 'mediális'), ('molaris', 'moláris'),
    ('verticalis', 'vertikális'), ('gingivalis', 'gingivális'), ('sulcularis', 'szulkuláris'),
    ('sulcus', 'szulkusz'), ('fibroticus', 'fibrotikus'), ('impactió', 'impakció'),
    ('impactio', 'impakció'), ('raspatórium', 'rászpatórium'), ('fissura', 'fisszúra'),
    ('cysta', 'ciszta'), ('septum', 'szeptum'), ('ramus', 'rámusz'), ('Lecluse', 'Leklüz'),
    ('Barry', 'Berri'), ('Lucas', 'Lúkász'), ('arteria', 'artéria'), ('maxillaris', 'maxilláris'),
    ('externa', 'exszterna'), ('trigonum', 'trigónum'), ('retromolare', 'retromoláre'),
    ('envelope', 'envelop'),
]
FIXED = [
    (' – 6.8. ábra: Barry-féle emelő.', '.'),
    ('2. és 3. nehézségi', 'második és harmadik nehézségi'),
    ('4/5', 'négyötöd'), ('1/3-ánál', 'egyharmadánál'), ('1/3-áig', 'egyharmadáig'),
    ('2–3 mm-rel', 'két-három milliméterrel'), ('15–20 mm-nél', 'tizenöt-húsz milliméternél'),
    ('45 fokban', 'negyvenöt fokban'),
    ('2. molaris', 'második molaris'), ('1. őrlőfog', 'első őrlőfog'), ('2. őrlőfog', 'második őrlőfog'),
    ('1.–2.', 'első és második'),
]

def speakable(t: str) -> str:
    for a, b in FIXED:
        t = t.replace(a, b)
    # ábrahivatkozások elhagyása
    t = re.sub(r'\s*[–-]\s*\d+\.\d+\.(\s*és\s*\d+\.\d+\.)?\s*ábra', '', t)
    t = re.sub(r'\s*\(\d+\.\d+\.(\s*és\s*\d+\.\d+\.)?\s*ábra\)', '', t)
    t = re.sub(r'\bn\. ', 'nervusz ', t)
    t = t.replace('„', '').replace('”', '')
    for a, b in STEMS:
        t = t.replace(a, b).replace(a.capitalize(), b.capitalize())
    t = t.strip()
    t = re.sub(r'^…\s*', '', t)
    t = re.sub(r'\s*…$', ',', t)
    t = t.replace(' – ', ', ').replace('–', '-')
    t = re.sub(r'\s+,', ',', t)
    return t

def captions():
    out = subprocess.run(['node', os.path.join(HERE, 'render.js'), 'texts'], capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])

def wav_dur(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()

def synth(voice):
    os.makedirs(CLIPS, exist_ok=True)
    scenes = captions()
    durs, script = [], []
    for si, caps in enumerate(scenes):
        row = []
        for ci, c in enumerate(caps):
            s = speakable(c)
            p = os.path.join(CLIPS, f's{si:02d}_c{ci:02d}.wav')
            subprocess.run([sys.executable, '-m', 'piper', '-m', voice, '-f', p, '--length-scale', '1.03'],
                           input=s, text=True, check=True, capture_output=True)
            row.append(round(wav_dur(p), 3))
            script.append(f'[{si}.{ci}] {s}')
        durs.append(row)
        print(f'jelenet {si}: {row}')
    with open(os.path.join(HERE, 'narration_timing.js'), 'w', encoding='utf-8') as f:
        f.write('// A felolvasás hossza feliratonként (s) – narrate.py generálja\nwindow.NARR_DUR = ' + json.dumps(durs) + ';\n')
    with open(os.path.join(OUT, 'felolvasott_szoveg.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(script) + '\n')

def mix():
    caps = json.load(open(os.path.join(OUT, 'captions.json'), encoding='utf-8'))
    total = caps['total']
    sr = None; buf = None
    for c in caps['items']:
        p = os.path.join(CLIPS, f"s{c['si']:02d}_c{c['ci']:02d}.wav")
        with wave.open(p) as w:
            if sr is None:
                sr = w.getframerate(); buf = np.zeros(int((total + 1) * sr), dtype=np.float32)
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        st = int((c['start'] + 0.15) * sr)
        buf[st:st + len(a)] += a[:len(buf) - st]
    buf = buf[:int(total * sr)]
    peak = np.max(np.abs(buf)) or 1
    buf = (buf / peak * 0.89 * 32767).astype(np.int16)
    wp = os.path.join(OUT, 'narration.wav')
    with wave.open(wp, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(buf.tobytes())
    src = os.path.join(OUT, 'bolcsessegfog_mutet.mp4'); tmp = os.path.join(OUT, 'tmp_av.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-i', wp, '-map', '0:v', '-map', '0:s?', '-map', '1:a',
                    '-c:v', 'copy', '-c:s', 'copy', '-c:a', 'aac', '-b:a', '128k', '-ar', '44100',
                    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-metadata:s:a:0', 'language=hun',
                    '-movflags', '+faststart', '-shortest', tmp], check=True)
    os.replace(tmp, src)
    os.remove(wp)
    print('Hangsáv hozzáadva:', src)

if __name__ == '__main__':
    if sys.argv[1] == 'synth':
        synth(sys.argv[2])
    else:
        mix()
