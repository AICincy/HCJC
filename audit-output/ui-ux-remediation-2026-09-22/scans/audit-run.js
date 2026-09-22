/* UI/UX audit harness for JCStream (aretheyinjail.com) served locally at :8777 */
const fs = require('fs');
const path = require('path');
const { getBrowser } = require('./launch.js');

const BASE = 'http://127.0.0.1:8777';
const OUT = process.env.OUT_DIR || path.join(__dirname, 'out');
fs.mkdirSync(path.join(OUT, 'shots'), { recursive: true });

const AXE_SRC = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 390, height: 844 },
  narrow: { width: 320, height: 600 }, // WCAG 1.4.10 reflow width
};

async function axeScan(page, context) {
  return page.evaluate((ctx) => {
    /* global axe */
    return axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
      resultTypes: ['violations'],
      context: { include: [ctx || document.body] },
    }).then((r) => ({
      violations: r.violations.map((v) => ({
        id: v.id, impact: v.impact, help: v.help, tags: v.tags.filter((t) => t.startsWith('wcag')),
        nodes: v.nodes.slice(0, 8).map((n) => ({ target: n.target, html: n.html.slice(0, 220), failureSummary: (n.failureSummary || '').slice(0, 300) })),
        nodeCount: v.nodes.length,
        any: (v.nodes[0] ? v.nodes[0].any || [] : []).map((a) => a.message).slice(0, 3),
      })),
      passes: r.passes.length, incomplete: r.incomplete.length,
    }));
  }, context);
}

async function pageMetrics(page) {
  return page.evaluate(() => {
    const all = [...document.querySelectorAll('*')];
    const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map((h) => ({ tag: h.tagName, text: (h.textContent || '').trim().slice(0, 80) }));
    return {
      domNodes: all.length,
      imgs: document.images.length,
      imgsNoAlt: [...document.images].filter((i) => !i.hasAttribute('alt')).length,
      docHeight: document.documentElement.scrollHeight,
      headings,
      title: document.title,
    };
  });
}

// Visible text elements with computed font-size below threshold
async function smallFontScan(page, minPx = 12) {
  return page.evaluate((min) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const seen = new Set(); const out = [];
    let n;
    while ((n = walker.nextNode())) {
      const t = (n.textContent || '').trim();
      if (!t) continue;
      const el = n.parentElement;
      if (!el || seen.has(el)) continue;
      seen.add(el);
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      const fs = parseFloat(cs.fontSize);
      if (fs < min) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        out.push({ fs, text: t.slice(0, 60), cls: (el.className || '').toString().slice(0, 60), tag: el.tagName });
      }
    }
    out.sort((a, b) => a.fs - b.fs);
    return out.slice(0, 60);
  }, minPx);
}

// Tap targets: interactive elements whose bounding box is under WCAG 2.5.8's 24x24
async function tapTargetScan(page) {
  return page.evaluate(() => {
    const sels = 'a, button, summary, input, select, [role="button"], [role="tab"]';
    const out = [];
    for (const el of document.querySelectorAll(sels)) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      // skip inline text links inside paragraphs/lists (sentence exception + spacing rule)
      const inline = ['P', 'LI', 'SPAN', 'SMALL', 'FOOTER', 'TD', 'TH'].includes(el.parentElement?.tagName) && cs.display.startsWith('inline');
      if (r.width < 24 || r.height < 24) {
        out.push({ w: +r.width.toFixed(1), h: +r.height.toFixed(1), tag: el.tagName, cls: (el.className || '').toString().slice(0, 50), text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40), inline });
      }
    }
    out.sort((a, b) => a.w * a.h - b.w * b.h);
    return out.slice(0, 80);
  });
}

async function newPage(browser, vp, theme) {
  const ctx = await browser.newContext({ viewport: VIEWPORTS[vp], bypassCSP: true });
  const page = await ctx.newPage();
  await page.addInitScript((t) => {
    try { localStorage.setItem('jcstream-theme', t); } catch (e) {}
  }, theme);
  return { ctx, page };
}

async function run() {
  const report = { startedAt: new Date().toISOString(), pages: {} };
  let browser = await getBrowser();

  const pages = JSON.parse(fs.readFileSync(path.join(__dirname, 'pages.json'), 'utf8'));

  for (const cfg of pages) {
    for (const vp of cfg.viewports || ['desktop', 'mobile']) {
      for (const theme of cfg.themes || ['dark', 'light']) {
        const key = `${cfg.name}|${vp}|${theme}`;
        try {
          if (!browser.isConnected()) { console.log('browser died, relaunching'); browser = await getBrowser(); }
          const { ctx, page } = await newPage(browser, vp, theme);
          await page.goto(BASE + cfg.path, { waitUntil: 'load', timeout: 60000 });
          await page.waitForTimeout(cfg.settle || 800);
          await page.addScriptTag({ content: AXE_SRC }); // CSP disabled via launch flags
          const axe = await axeScan(page);
          const metrics = await pageMetrics(page);
          const small = vp === 'mobile' || cfg.smallFontAlways ? await smallFontScan(page) : null;
          const taps = vp === 'mobile' ? await tapTargetScan(page) : null;
          const shot = `${cfg.name}-${vp}-${theme}`;
          const tall = metrics.docHeight;
          await page.screenshot({ path: path.join(OUT, 'shots', `${shot}-fold.png`) });
          if (cfg.full && tall <= 30000) {
            await page.screenshot({ path: path.join(OUT, 'shots', `${shot}-full.png`), fullPage: true });
          } else if (cfg.full) {
            await page.screenshot({ path: path.join(OUT, 'shots', `${shot}-clipped.png`), clip: { x: 0, y: 0, width: VIEWPORTS[vp].width, height: 30000 } });
          }
          report.pages[key] = { path: cfg.path, axe, metrics: { ...metrics, headings: undefined }, headings: metrics.headings, smallFonts: small, tapTargets: taps, docHeight: tall };
          await ctx.close();
          console.log('done', key, `violations=${axe.violations.length} domNodes=${metrics.domNodes} h=${tall}`);
        } catch (e) {
          report.pages[key] = { path: cfg.path, error: e.message.split('\n')[0] };
          console.log('ERROR', key, e.message.split('\n')[0]);
        }
      }
    }
  }
  await browser.close();
  fs.writeFileSync(path.join(OUT, 'axe-report.json'), JSON.stringify(report, null, 1));
  console.log('WROTE', path.join(OUT, 'axe-report.json'));
}
run().catch((e) => { console.error(e); process.exit(1); });
