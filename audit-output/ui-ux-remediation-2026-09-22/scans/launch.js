const path = require('path');
const { chromium } = require('playwright');
const pkg = require('@sparticuz/chromium');
const Chromium = pkg.default;
const inflate = pkg.inflate;

async function getBrowser(opts = {}) {
  const execPath = await Chromium.executablePath();       // /tmp/chromium + fonts + swiftshader
  const binDir = path.join(path.join(process.cwd(), 'node_modules', '@sparticuz', 'chromium'), 'bin');
  await inflate(path.join(binDir, 'al2023.tar.br'));      // -> /tmp/al2023/lib
  process.env.LD_LIBRARY_PATH = '/tmp/al2023/lib:' + (process.env.LD_LIBRARY_PATH || '');
  const args = Chromium.args.filter((a) => a !== '--single-process' && a !== '--no-zygote');
  return chromium.launch({
    executablePath: execPath,
    args: [...args, '--disable-gpu'],
    headless: true,
    env: { ...process.env },
    ...opts,
  });
}
module.exports = { getBrowser };
if (require.main === module) {
  (async () => {
    const b = await getBrowser();
    const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
    await p.goto('https://www.aretheyinjail.com/', { waitUntil: 'load', timeout: 90000 });
    await p.screenshot({ path: 'smoke.png' });
    console.log('OK title=', await p.title());
    await b.close();
  })().catch(e => { console.error('FAIL:', e.message.split('\n').slice(0,6).join(' | ')); process.exit(1); });
}
