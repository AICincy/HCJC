/* Browser regression gates for the 2026-09-22 UI findings.
   Run against a freshly built site. See design/ui-remediation.md for setup.
   Optional CHROMIUM_EXECUTABLE supports a system/headless browser. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8777';
const OUT = process.env.UI_REPORT_DIR || '.cache/ui-verification';
const axePath = require.resolve('axe-core/axe.min.js');

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({
    ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}),
    args: ['--no-sandbox', '--disable-gpu'], headless: true,
  });
  const report = { capturedAt: new Date().toISOString(), axeVersion: require('axe-core/package.json').version, scans: [], checks: [] };
  try {
    const p = await browser.newPage();
    const response = await p.goto(BASE + '/');
    assert.equal(response.status(), 200);
    const previewIDs = await p.locator('.card-inmate').evaluateAll(nodes => nodes.map(n => n.getAttribute('aria-labelledby')));
    assert(previewIDs.length <= 48 && previewIDs.length > 0);
    const index = await (await p.request.get(BASE + '/search.json')).json();
    const outside = index.rows.find(r => !previewIDs.includes('card-' + r.id + '-name'));
    assert(outside, 'Fixture needs a record outside the initial 48');
    await p.locator('#search-box').fill('#' + outside.id);
    await p.locator('#search-results a[href$="/inmate/' + outside.id + '/"]').waitFor();
    assert(await p.locator('#filter-empty').isHidden(), 'Never claim a preview-only miss');
    await p.locator('#search-box').press('Enter');
    await p.waitForURL('**/archive/**');
    await p.waitForFunction(() => document.querySelector('.filter-count').textContent.includes('matching'));
    assert.equal(await p.locator('.card-inmate:not(.is-filtered-out)').count(), 1);
    report.checks.push('Full-roster dropdown and Enter submission find a record outside the preview');

    await p.goto(BASE + '/?tier=f2');
    await p.waitForURL('**/archive/?tier=f2');
    await p.waitForFunction(() => document.querySelector('#filter-tier').value === 'f2');
    assert(await p.locator('.card-inmate:not(.is-filtered-out)').count() > 0);
    assert.equal(await p.locator('.card-inmate:not(.is-filtered-out):not([data-degree="F2"])').count(), 0);
    await p.goto(BASE + '/archive/?page=2');
    await p.waitForFunction(() => document.querySelector('.pager-num[aria-current="page"]')?.textContent === '2');
    await p.reload();
    await p.waitForFunction(() => document.querySelector('.pager-num[aria-current="page"]')?.textContent === '2');
    await p.goto(BASE + '/?sort=name');
    await p.waitForURL('**/archive/?sort=name');
    await p.waitForFunction(() => document.querySelector('#filter-sort').value === 'name' && !document.querySelector('#sort-bin').hidden);
    for (const sort of ['name', 'custody', 'degree']) {
      await p.goto(BASE + '/?sort=' + sort + '&page=2&pagesize=48&tier=f2');
      await p.waitForURL('**/archive/**');
      for (let reload = 0; reload < 2; reload++) {
        if (reload) await p.reload();
        await p.waitForFunction(() => document.querySelector('#sort-bin .pager-num[aria-current="page"]')?.textContent === '2');
        assert.equal(new URL(p.url()).searchParams.get('page'), '2');
        assert.equal(await p.locator('#filter-sort').inputValue(), sort);
        assert.equal(await p.locator('#filter-tier').inputValue(), 'f2');
        assert.equal(await p.locator('#sort-bin .pager-size-sel').inputValue(), '48');
        assert(await p.locator('#sort-bin .card-inmate:not(.is-filtered-out):not(.is-paged-out)').count() > 0);
      }
    }
    await p.locator('.more-filters summary').click();
    await p.locator('#filter-sort').selectOption('name');
    assert.equal(await p.locator('#sort-bin .pager-num[aria-current="page"]').textContent(), '1');
    await p.goto(BASE + '/archive/?sort=name&page=999999');
    const lastPage = String(Math.ceil(index.rows.length / 24));
    assert.equal(await p.locator('#sort-bin .pager-num[aria-current="page"]').textContent(), lastPage);
    assert.equal(new URL(p.url()).searchParams.get('page'), lastPage);
    report.checks.push('Tier, sort, and page deep links survive navigation/reload, including combined sort/filter/page-size links and out-of-range clamping');
    await p.goto(BASE + '/archive/');
    const monthID = await p.locator('details.month').last().getAttribute('id');
    await p.goto(BASE + '/#' + monthID);
    await p.waitForURL('**/archive/#' + monthID);
    for (let reload = 0; reload < 2; reload++) {
      if (reload) await p.reload();
      assert(await p.locator('#' + monthID).evaluate(n => n.open));
      assert(await p.locator('#' + monthID + ' .card-inmate').count() > 0);
    }
    report.checks.push('Homepage month fragment forwards to the full archive and opens the matching month after reload');

    await p.goto(BASE + '/');
    await p.locator('.more-filters summary').focus();
    await p.keyboard.press('Enter');
    assert(await p.locator('#filter-tier').isVisible());
    await p.locator('#filter-tier').selectOption('misdemeanor');
    await p.waitForURL('**/archive/**');
    await p.waitForFunction(() => document.querySelector('#filter-tier').value === 'misdemeanor');
    report.checks.push('Keyboard disclosure and preview filter submit to the full roster');
    await p.goto(BASE + '/');
    const badge = p.locator('.card-inmate button.tier').first();
    // Park the pointer away from the roster before testing keyboard-only focus.
    await p.mouse.move(0, 0);
    await badge.scrollIntoViewIfNeeded();
    await badge.focus();
    await p.locator('#tier-tip').waitFor({state: 'visible'});
    assert.equal(await badge.getAttribute('aria-describedby'), 'tier-tip');
    await p.keyboard.press('Escape');
    assert(await p.locator('#tier-tip').isHidden());
    report.checks.push('Tier tooltip works from focus and Escape');
    await p.close();

    const noJS = await browser.newPage({javaScriptEnabled: false});
    await noJS.goto(BASE + '/');
    await noJS.locator('.roster-preview-note a').click();
    await noJS.waitForLoadState('load');
    assert.equal(await noJS.locator('.card-inmate').count(), index.rows.length);
    await noJS.close();
    report.checks.push('No-JavaScript archive exposes every current record');

    const recordPath = '/inmate/' + outside.id + '/';
    const routes = ['/', '/help/', '/stats/', '/courts/', '/judges/', '/bond-schedule/', '/data/',
      '/transparency/', '/archive/', '/visit/', '/404.html', recordPath];
    for (const route of routes) for (const width of [1440, 390, 320]) for (const theme of ['dark', 'light']) {
      // CSP bypass is only for injecting axe; application tests above used the real CSP.
      const page = await browser.newPage({bypassCSP: true, viewport: {width, height: 900}});
      const res = await page.goto(BASE + route);
      assert.equal(res.status(), 200, route);
      await page.evaluate(t => document.documentElement.dataset.theme = t, theme);
      await page.addScriptTag({path: axePath});
      const scan = await page.evaluate(async () => {
        const result = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});
        return {
          violations: result.violations.map(v => ({id: v.id, nodes: v.nodes.map(n => ({target: n.target, summary: n.failureSummary}))})),
          documentWidth: document.documentElement.scrollWidth, viewportWidth: innerWidth,
          searchSize: document.querySelector('#search-box') ? getComputedStyle(document.querySelector('#search-box')).fontSize : null,
          badges: [...document.querySelectorAll('.card-inmate button.tier')].filter(n => n.checkVisibility()).map(n => ({w:n.getBoundingClientRect().width,h:n.getBoundingClientRect().height})),
          tables: [...document.querySelectorAll('table.stackable')].map(n => ({w:n.getBoundingClientRect().width,scroll:n.parentElement.scrollWidth,client:n.parentElement.clientWidth})),
        };
      });
      report.scans.push({route, width, theme, ...scan});
      fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
      assert.deepEqual(scan.violations, [], route + ' ' + width + ' ' + theme);
      assert(scan.documentWidth <= width, route + ' document overflow');
      if (scan.searchSize) assert(parseFloat(scan.searchSize) >= 16);
      scan.badges.forEach(b => assert(b.w >= 24 && b.h >= 24));
      if (width <= 720) scan.tables.forEach(t => assert(t.scroll <= t.client + 1, 'stacked table overflow'));
      if (['/', '/help/', '/bond-schedule/', recordPath].includes(route) &&
          ((width === 1440 && theme === 'dark') || (width === 390 && theme === 'dark') || (width === 320 && theme === 'light'))) {
        const name = route === '/' ? 'home' : route === recordPath ? 'record' : route.replaceAll('/', '');
        await page.screenshot({path: path.join(OUT, `${name}-${width}-${theme}.png`), fullPage: false});
      }
      await page.close();
    }
    report.checks.push('72 axe scans, reflow, input type size, tier target sizes, and responsive table bounds passed');
    // Stress long identifiers without changing source records.
    const stress = await browser.newPage({viewport:{width:320,height:900}});
    await stress.goto(BASE + recordPath);
    await stress.locator('table.stackable .cell-value').first().evaluate(n => n.textContent = 'LONG-STATUTE-AND-CASE-IDENTIFIER'.repeat(5));
    assert(await stress.evaluate(() => document.documentElement.scrollWidth === innerWidth));
    await stress.close();
    report.checks.push('320px long-identifier reflow passed');
    for (const width of [320, 375, 390, 412, 768, 1024, 1440]) for (const theme of ['dark', 'light']) {
      const page = await browser.newPage({viewport:{width,height:900}});
      for (const route of ['/', '/bond-schedule/', recordPath]) {
        await page.goto(BASE + route);
        await page.evaluate(t => document.documentElement.dataset.theme = t, theme);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        if (route === recordPath && width <= 720) {
          assert(await page.locator('.record-detail').evaluate(n => getComputedStyle(n).gridColumnStart === '1'));
        }
        if (route !== '/' && width <= 720) {
          const table = page.locator('table.stackable');
          await table.scrollIntoViewIfNeeded();
          assert(await table.evaluate(n => n.parentElement.scrollWidth <= n.parentElement.clientWidth + 1));
          if ((width === 390 && theme === 'dark') || (width === 320 && theme === 'light')) {
            await page.screenshot({path:path.join(OUT, (route === recordPath ? 'charges' : 'schedule') + '-' + width + '-' + theme + '.png')});
          }
        }
      }
      await page.close();
    }
    report.checks.push('Home, bond, and record layout checks at 320/375/390/412/768/1024/1440 in both themes passed');

    fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
    console.log('PASS', report.checks);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
