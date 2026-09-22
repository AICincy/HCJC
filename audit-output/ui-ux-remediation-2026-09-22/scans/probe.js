const path = require('path');
const { getBrowser } = require('./launch.js');
const fs = require('fs');

const BASE = 'http://127.0.0.1:8777';
const OUT = process.env.OUT_DIR || path.join(__dirname, 'out');
fs.mkdirSync(OUT, { recursive: true });

function lum(r,g,b){const f=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4)};return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)}
function ratio(c1,c2){const l1=lum(...c1),l2=lum(...c2);const[a,b]=l1>l2?[l1,l2]:[l2,l1];return (a+0.05)/(b+0.05)}
function parse(s){const m=s.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);if(!m)return null;return {r:+m[1],g:+m[2],b:+m[3],a:m[4]===undefined?1:+m[4]}}
function effColor(color, bgStack){ // composite alpha over first opaque bg in stack
  let c = parse(color); if(!c) return null;
  if (c.a >= 1) return [c.r,c.g,c.b];
  for (const bg of bgStack){ const b=parse(bg); if(!b) continue;
    return [Math.round(c.r*c.a+b.r*(1-c.a)), Math.round(c.g*c.a+b.g*(1-c.a)), Math.round(c.b*c.a+b.b*(1-c.a))]; }
  return [c.r,c.g,c.b];
}

async function probePage(page, name, checks) {
  const data = await page.evaluate((ck) => {
    const out = {};
    const cs = (el) => getComputedStyle(el);
    const bgStack = (el) => { // walk up for backgrounds
      const stack = []; let n = el;
      while (n && n !== document.documentElement) { const s = cs(n); if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)') stack.push(s.backgroundColor); n = n.parentElement; }
      stack.push(cs(document.documentElement).backgroundColor || 'rgb(255,255,255)');
      return stack;
    };
    if (ck.includes('typography')) {
      const sels = ['body', 'h1', '.section-h h1', '.section-h h2', 'h2', 'h3', '.card-inmate .name', '.card-inmate .charge', '.card-inmate .id-chip', 'p', 'a', '.masthead .brand-name', '.kpi .num', '.kpi .label', '.meta', 'footer.site span'];
      out.typography = {};
      for (const s of sels) { const el = document.querySelector(s); if (!el) continue; const c = cs(el);
        out.typography[s] = { fontSize: c.fontSize, weight: c.fontWeight, family: c.fontFamily.split(',')[0].replace(/"/g,''), lineHeight: c.lineHeight, ls: c.letterSpacing }; }
    }
    if (ck.includes('placeholder')) {
      const el = document.querySelector('#search-box'); if (el) {
        let pc = cs(el)['::placeholder'] ? cs(el)['::placeholder'].color : null;
        out.placeholder = { placeholderRule: pc, inputBg: cs(el).backgroundColor, inputFg: cs(el).color, attr: el.getAttribute('placeholder') };
        // try getComputedStyle for pseudo via CSSOM
        const st = getComputedStyle(el, '::placeholder');
        out.placeholder.pseudo = { color: st.color, opacity: st.opacity };
      }
    }
    if (ck.includes('overflow')) {
      const d = document.documentElement;
      out.overflow = { scrollW: d.scrollWidth, clientW: d.clientWidth, hasHScroll: d.scrollWidth > d.clientWidth };
      // find offenders
      out.offenders = [];
      for (const el of document.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        if (r.right > d.clientWidth + 1 || r.left < -1) {
          if (out.offenders.length < 12 && cs(el).position !== 'fixed') out.offenders.push({ tag: el.tagName, cls: (el.className||'').toString().slice(0,40), right: Math.round(r.right), left: Math.round(r.left), w: Math.round(r.width) });
        }
      }
    }
    if (ck.includes('kpi')) {
      const el = document.querySelector('.kpi:nth-child(1) .label') || document.querySelector('.kpi .label');
      if (el) { const c = cs(el); out.kpi = { color: c.color, fs: c.fontSize, fw: c.fontWeight, bgStack: bgStack(el), text: el.textContent.trim() }; }
    }
    if (ck.includes('masthead')) {
      const m = document.querySelector('.masthead-inner');
      const h = document.querySelector('.masthead');
      const brand = document.querySelector('.brand-name');
      const toggle = document.querySelector('.theme-toggle');
      const nav = document.querySelector('.nav-toggle');
      out.masthead = { innerH: m ? Math.round(m.getBoundingClientRect().height) : null, mastheadH: h ? Math.round(h.getBoundingClientRect().height) : null,
        brandFs: brand ? cs(brand).fontSize : null, toggle: toggle ? { w: Math.round(toggle.getBoundingClientRect().width), h: Math.round(toggle.getBoundingClientRect().height) } : null,
        nav: nav ? { w: Math.round(nav.getBoundingClientRect().width), h: Math.round(nav.getBoundingClientRect().height) } : null };
    }
    if (ck.includes('chargesTable')) {
      const t = document.querySelector('table.charges');
      if (t) { const r = t.getBoundingClientRect(); const wrap = t.parentElement;
        out.charges = { tableW: Math.round(r.width), wrapScrollW: wrap ? wrap.scrollWidth : null, wrapClientW: wrap ? wrap.clientWidth : null, overflowX: wrap ? cs(wrap).overflowX : null }; }
    }
    if (ck.includes('linkStyle')) {
      const a = document.querySelector('.page p a, p a, .doc-wrap a');
      if (a) { const c = cs(a); out.linkStyle = { color: c.color, textDecoration: c.textDecorationLine, thickness: c.textDecorationThickness }; }
    }
    return out;
  }, checks);
  console.log('=====', name, JSON.stringify(data, null, 1).slice(0, 3500));
  return data;
}

(async () => {
  const browser = await getBrowser();
  const results = {};

  // Home desktop dark: typography, placeholder, linkStyle
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    await p.goto(BASE + '/', { waitUntil: 'load' });
    results.homeDesktop = await probePage(p, 'home-desktop-dark', ['typography', 'placeholder', 'linkStyle']);
    await ctx.close();
  }
  // Home narrow dark: overflow
  {
    const ctx = await browser.newContext({ viewport: { width: 320, height: 600 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    await p.goto(BASE + '/', { waitUntil: 'load' });
    results.homeNarrow = await probePage(p, 'home-320-dark', ['overflow']);
    await ctx.close();
  }
  // Inmate mobile dark: charges table overflow
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    await p.goto(BASE + '/inmate/1821276/', { waitUntil: 'load' });
    results.inmateMobile = await probePage(p, 'inmate-mobile-dark', ['overflow', 'chargesTable', 'typography']);
    await ctx.close();
  }
  // Stats dark: kpi label + light theme linkStyle
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    await p.goto(BASE + '/stats/', { waitUntil: 'load' });
    results.statsDark = await probePage(p, 'stats-desktop-dark', ['kpi', 'typography']);
    await ctx.close();
  }
  // Home mobile light: masthead + linkStyle light
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'light'));
    await p.goto(BASE + '/', { waitUntil: 'load' });
    results.homeMobileLight = await probePage(p, 'home-mobile-light', ['masthead', 'linkStyle', 'placeholder']);
    await ctx.close();
  }
  // Bond schedule mobile: table overflow check
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, bypassCSP: true });
    const p = await ctx.newPage();
    await p.addInitScript(() => localStorage.setItem('jcstream-theme', 'dark'));
    await p.goto(BASE + '/bond-schedule/', { waitUntil: 'load' });
    results.bondMobile = await probePage(p, 'bond-mobile-dark', ['overflow']);
    await ctx.close();
  }

  fs.writeFileSync(path.join(OUT, 'probe-results.json'), JSON.stringify(results, null, 1));
  await browser.close();
  console.log('DONE');
})().catch((e) => { console.error(e); process.exit(1); });
