const path = require('path');
const { getBrowser } = require('./launch.js');
const fs = require('fs');
const BASE = 'http://127.0.0.1:8777';
const OUT = path.join(__dirname, 'out');

(async () => {
  const browser = await getBrowser();
  const log = {};

  // ---- 1. Keyboard tab-through on home (dark, desktop) ----
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    await p.goto(BASE + '/', { waitUntil: 'load' });
    const stops = [];
    for (let i = 0; i < 12; i++) {
      await p.keyboard.press('Tab');
      const info = await p.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return { tag: 'body' };
        const cs = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        const o = getComputedStyle(el, ':focus-visible') || {};
        return {
          tag: el.tagName, id: el.id || '', cls: (el.className || '').toString().slice(0, 40),
          text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 30),
          outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}`,
          boxShadow: cs.boxShadow !== 'none' ? cs.boxShadow.slice(0, 60) : 'none',
          inViewport: r.top >= 0 && r.bottom <= innerHeight,
        };
      });
      stops.push(info);
    }
    log.tabStops = stops;
    // screenshot the focused search input + a focused tier badge
    await p.keyboard.press('Home');
    await p.evaluate(() => { const el = document.querySelector('#search-box'); el.blur(); el.focus(); });
    await p.screenshot({ path: path.join(OUT, 'shots', 'focus-search.png'), clip: { x: 0, y: 0, width: 1440, height: 320 } });
    await p.evaluate(() => { document.querySelector('.card-inmate .tier')?.focus(); });
    await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(OUT, 'shots', 'focus-tier.png'), clip: { x: 0, y: 100, width: 1440, height: 420 } });
    const tip = await p.evaluate(() => { const t = document.getElementById('tier-tip'); return { hidden: t.hidden, text: t.textContent.slice(0, 120), rect: t.getBoundingClientRect().toJSON() }; });
    log.tierTipOnFocus = tip;

    // ---- 2. Search interaction ----
    await p.fill('#search-box', 'jones');
    await p.waitForTimeout(700);
    const sr = await p.evaluate(() => {
      const panel = document.getElementById('search-results');
      const status = document.getElementById('search-status');
      const items = panel ? panel.querySelectorAll('.sr-item').length : 0;
      return { panelHidden: panel ? panel.hidden : null, items, statusText: status ? status.textContent : null,
        visibleCards: [...document.querySelectorAll('.card-inmate')].filter((c) => c.offsetParent !== null).length };
    });
    log.search = sr;
    await p.screenshot({ path: path.join(OUT, 'shots', 'search-dropdown.png'), clip: { x: 0, y: 0, width: 1440, height: 480 } });

    // ---- 3. Filters disclosure + tier filter ----
    await p.click('.more-filters summary');
    await p.waitForTimeout(200);
    await p.screenshot({ path: path.join(OUT, 'shots', 'filters-open.png'), clip: { x: 0, y: 0, width: 1440, height: 560 } });
    // more-filters summary focus ring?
    await p.focus('.more-filters summary');
    log.filtersSummaryFocus = await p.evaluate(() => {
      const el = document.querySelector('.more-filters summary');
      el.focus();
      const cs = getComputedStyle(el);
      return { outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}` };
    });

    // ---- 4. Theme toggle ----
    const themeBefore = await p.evaluate(() => document.documentElement.getAttribute('data-theme'));
    await p.click('.theme-toggle');
    await p.waitForTimeout(200);
    const themeAfter = await p.evaluate(() => document.documentElement.getAttribute('data-theme'));
    log.themeToggle = { before: themeBefore, after: themeAfter };
    await ctx.close();
  }

  // ---- 5. Lightbox (inmate page) ----
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    await p.goto(BASE + '/inmate/1821276/', { waitUntil: 'load' });
    const thumb = await p.$('.thumb[data-photo]');
    if (thumb) {
      await thumb.click();
      await p.waitForTimeout(400);
      log.lightbox = await p.evaluate(() => {
        const lb = document.getElementById('lb');
        return { open: !lb.hidden, focused: document.activeElement && document.activeElement.className, inertApplied: [...document.body.children].filter((n) => n.inert).length };
      });
      await p.screenshot({ path: path.join(OUT, 'shots', 'lightbox.png') });
      await p.keyboard.press('Escape');
      log.lightbox.afterEsc = await p.evaluate(() => ({ hidden: document.getElementById('lb').hidden, focusRestored: document.activeElement.className || document.activeElement.tagName }));
    }
    await ctx.close();
  }

  // ---- 6. Page weight / perf (home) ----
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    const entries = [];
    p.on('response', (r) => entries.push({ url: r.url().replace(BASE, ''), status: r.status(), type: r.request().resourceType() }));
    const t0 = Date.now();
    await p.goto(BASE + '/', { waitUntil: 'load' });
    const loadMs = Date.now() - t0;
    const perf = await p.evaluate(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      const res = performance.getEntriesByType('resource');
      const byType = {};
      for (const r of res) { byType[r.initiatorType] = (byType[r.initiatorType] || 0) + 1; }
      return {
        transferSize: nav ? nav.transferSize : null,
        domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
        loadEvent: nav ? Math.round(nav.loadEventEnd) : null,
        resources: res.length, byType,
        imgBytes: res.filter((r) => r.initiatorType === 'img').reduce((a, r) => a + (r.transferSize || 0), 0),
        imgCount: res.filter((r) => r.initiatorType === 'img').length,
      };
    });
    log.perf = { localLoadMs: loadMs, ...perf, bigAssets: entries.filter((e) => /json|js|css|xml/.test(e.url)).slice(0, 20) };
    await ctx.close();
  }

  fs.writeFileSync(path.join(OUT, 'interact-results.json'), JSON.stringify(log, null, 1));
  console.log(JSON.stringify(log, (k, v) => (k === 'bigAssets' ? `(${v.length} assets)` : v), 1).slice(0, 4500));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
