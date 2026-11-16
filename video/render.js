// Képkockánkénti renderelés: node render.js [video|preview|srt]
// video:   out/bolcsessegfog_mutet.mp4 (+ .srt) – párhuzamos szegmensekben
// preview: kulcsképek PNG-ben a vizuális ellenőrzéshez
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 25;
const HTML = 'file://' + path.resolve(__dirname, 'animation.html') + '?render';
const OUT = path.resolve(__dirname, 'out');
fs.mkdirSync(OUT, { recursive: true });

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errs = [];
  page.on('pageerror', e => errs.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await page.goto(HTML);
  await page.evaluate(() => window.READY);
  if (errs.length) throw new Error(errs.join('\n'));
  return page;
}
const fmt = t => {
  const ms = Math.round(t * 1000), h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, s = Math.floor(ms / 1000) % 60, r = ms % 1000;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(r).padStart(3, '0')}`;
};
async function writeSrt(page) {
  const caps = await page.evaluate(() => window.CAPTIONS());
  const srt = caps.map((c, i) => `${i + 1}\n${fmt(c.start)} --> ${fmt(c.end)}\n${c.text}\n`).join('\n');
  fs.writeFileSync(path.join(OUT, 'bolcsessegfog_mutet.hu.srt'), srt);
  const ch = await page.evaluate(() => window.CHAPTERS());
  fs.writeFileSync(path.join(OUT, 'fejezetek.txt'), ch.map(c => `${fmt(c.start).slice(0, 8)}  ${c.title}`).join('\n') + '\n');
  return caps.length;
}
async function renderSegment(browser, f0, f1, file) {
  const page = await openPage(browser);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', String(FPS), file], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = f0; f < f1; f++) {
    await page.evaluate(t => window.renderAt(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92, clip: { x: 0, y: 0, width: 1920, height: 1080 } });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 500 === 0) console.log(`  ${path.basename(file)}: ${f - f0}/${f1 - f0}`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
  await page.close();
}

(async () => {
  const mode = process.argv[2] || 'video';
  const browser = await chromium.launch();
  const page = await openPage(browser);
  if (mode === 'texts') { console.log(JSON.stringify(await page.evaluate(() => window.CAPTEXTS()))); await browser.close(); return; }
  const total = await page.evaluate(() => window.TOTAL);
  console.log('Teljes hossz:', total.toFixed(1), 's');
  // gyors hibakeresés: minden 0,2 s-ban kirajzol egy képkockát
  await page.evaluate(T => { for (let t = 0; t < T; t += 0.2) window.renderAt(t); }, total);
  console.log('Ellenőrzés OK');
  if (mode === 'preview') {
    const times = process.argv.slice(3).map(Number);
    for (const t of times) {
      await page.evaluate(t => window.renderAt(t), t);
      await page.screenshot({ path: path.join(OUT, `prev_${String(t).padStart(6, '0')}.png`) });
    }
  } else if (mode === 'chapters') {
    const ch = await page.evaluate(() => window.SCENESINFO ? null : window.CHAPTERS());
    console.log(JSON.stringify(ch));
    const caps = await page.evaluate(() => window.CAPTIONS());
    console.log(JSON.stringify(caps.map(c => [c.start.toFixed(1), c.end.toFixed(1)])));
  } else {
    console.log('Feliratok:', await writeSrt(page));
    const items = await page.evaluate(() => window.CAPTIONS());
    fs.writeFileSync(path.join(OUT, 'captions.json'), JSON.stringify({ total, items }));
    const N = Math.ceil(total * FPS), K = Number(process.env.WORKERS || 4);
    const per = Math.ceil(N / K), segs = [];
    for (let k = 0; k < K; k++) segs.push([k * per, Math.min(N, (k + 1) * per), path.join(OUT, `seg${k}.mp4`)]);
    const t0 = Date.now();
    await Promise.all(segs.map(([a, b, f]) => renderSegment(browser, a, b, f)));
    fs.writeFileSync(path.join(OUT, 'list.txt'), segs.map(s => `file '${s[2]}'`).join('\n'));
    const final = path.join(OUT, 'bolcsessegfog_mutet.mp4');
    await new Promise((res, rej) => {
      const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(OUT, 'list.txt'),
        '-i', path.join(OUT, 'bolcsessegfog_mutet.hu.srt'), '-map', '0:v', '-map', '1:s', '-c:v', 'copy', '-c:s', 'mov_text',
        '-metadata:s:s:0', 'language=hun', '-movflags', '+faststart', final], { stdio: 'inherit' });
      p.on('close', c => c === 0 ? res() : rej(new Error('concat ' + c)));
    });
    segs.forEach(s => fs.unlinkSync(s[2])); fs.unlinkSync(path.join(OUT, 'list.txt'));
    // felolvasás hozzáadása, ha a hangfájlok elkészültek (narrate.py synth)
    if (fs.existsSync(path.join(OUT, 'clips'))) {
      await new Promise((res, rej) => {
        const p = spawn('python3', [path.join(__dirname, 'narrate.py'), 'mix'], { stdio: 'inherit' });
        p.on('close', c => c === 0 ? res() : rej(new Error('narrate mix ' + c)));
      });
    }
    console.log('Kész:', final, ((Date.now() - t0) / 1000).toFixed(0), 's');
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
