// Progressive enhancement only - site is fully usable with JS disabled.
// External cache-busted via main_js_version (sha256 of this file's bytes).
// ROOT comes from <html data-base-url="..."> so this script needs no Jinja.
(function () {
  var ROOT = document.documentElement.dataset.baseUrl || '';

  // (1) Auto-open a collapsed <details> when it (or a child anchor) becomes
  //     the URL fragment, so the "Crimes of <Month>" chips work.
  function openDetailsFor(hash) {
    if (!hash || hash === '#' || hash === '#top') return;
    var el = document.getElementById(hash.replace(/^#/, ''));
    if (!el) return;
    var d = el.closest('details');
    if (d && !d.open) d.open = true;
    // Sticky masthead + month chips eat ~8rem; wait for <details> reflow
    // or the hash lands ~1000px short of the section heading.
    el.style.scrollMarginTop = el.style.scrollMarginTop || '8rem';
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        el.scrollIntoView({ block: 'start', behavior: 'auto' });
      });
    });
  }
  window.addEventListener('hashchange', function () { openDetailsFor(location.hash); });
  if (location.hash) openDetailsFor(location.hash);
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="#"]');
    if (a && a.getAttribute('href').length > 1) openDetailsFor(a.getAttribute('href'));
  });

  // (1b) Site nav drawer. Markup ships closed: mobile is a native disclosure
  // with no JS (H6 fix, B2); desktop renders the rail from closed markup via
  // the ::details-content CSS override. With JS, the drawer dismisses on
  // outside click on small screens and aria-expanded on the toggle is synced
  // for assistive technology (B2).
  var navMenu = document.querySelector('.nav-menu');
  if (navMenu && window.matchMedia) {
    var navMQ = window.matchMedia('(max-width: 720px)');
    var navToggle = navMenu.querySelector('.nav-toggle');
    var syncNavAria = function () {
      if (navToggle) navToggle.setAttribute('aria-expanded', navMenu.open ? 'true' : 'false');
    };
    navMenu.addEventListener('toggle', syncNavAria);
    syncNavAria();
    document.addEventListener('click', function (e) {
      if (navMQ.matches && navMenu.open && !navMenu.contains(e.target)) navMenu.removeAttribute('open');
    });
  }

  // (2) Shared lightbox.
  // Contract: every page extending base.html renders #lb, #lb-img, and #lb-cap.
  // Keep this bundle paired with that shared layout; standalone pages need their
  // own lightbox markup before this handler is evaluated.
  var lb = document.getElementById('lb');
  var lbImg = document.getElementById('lb-img');
  var lbCap = document.getElementById('lb-cap');
  var lastFocus = null;
  function openLB(src, caption, alt) {
    // src comes from a tainted [data-photo] DOM attribute. Extract just the
    // basename via a restricted regex ([\w.\-]+\.(jpe?g|png|webp|gif)), then
    // assign a URL built from constants + that capture, passed through encodeURI
    // - the canonical CodeQL js/xss-through-dom sanitizer. encodeURI is a no-op
    // for safe inputs (the regex already restricted the char class) and
    // explicitly signals "this is a URL, not HTML" to the static analyzer.
    // Returns false on no match so the caller can fall through to the href
    // (preserves the no-JS contract if the photo pipeline ever emits non-jpg).
    var m = typeof src === 'string' && src.match(/([\w.\-]+\.(?:jpe?g|png|webp|gif))$/i);
    if (!m) return false;
    lastFocus = document.activeElement;
    lbImg.src = encodeURI(ROOT + '/photos/' + m[1]);
    lbImg.alt = alt || 'Booking photo';
    lbCap.textContent = caption || '';
    lb.hidden = false;
    // Confine focus to the dialog: mark all other body children inert and aria-hidden.
    // Browsers without inert support fall back to the Tab cycler below.
    Array.prototype.forEach.call(document.body.children, function (n) {
      if (n !== lb) {
        n.inert = true;
        n.setAttribute('aria-hidden', 'true');
      }
    });
    lb.querySelector('.lightbox-close').focus();
    return true;
  }
  function closeLB() {
    lb.hidden = true; lbImg.removeAttribute('src');
    Array.prototype.forEach.call(document.body.children, function (n) {
      n.inert = false;
      n.removeAttribute('aria-hidden');
    });
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  lb.querySelector('.lightbox-backdrop').addEventListener('click', closeLB);
  lb.querySelector('.lightbox-close').addEventListener('click', closeLB);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !lb.hidden) closeLB();
  });
  // Tab cycler fallback for browsers without inert. Keeps focus inside #lb.
  lb.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab' || lb.hidden) return;
    var focusables = lb.querySelectorAll('button, [href], [tabindex]:not([tabindex="-1"])');
    if (!focusables.length) return;
    var first = focusables[0];
    var last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  });
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-photo]');
    if (!t) return;
    // Only swallow the click if the lightbox actually opened; otherwise let the
    // anchor navigate to its href (no-JS fallthrough preserved).
    if (openLB(t.getAttribute('data-photo'), t.getAttribute('data-photo-cap'), t.getAttribute('data-photo-alt'))) {
      e.preventDefault();
    }
  });

  // (2b) Shared tier-badge tooltip - content lives in [data-tip], JS positions it.
  //      Uses DOM APIs (not innerHTML) to avoid CodeQL DOM-text-reinterpreted-as-HTML.
  var tip = document.getElementById('tier-tip');
  if (tip) {
    var _activeBadge = null;
    function hideTip() {
      tip.hidden = true; tip.style.left = '-9999px';
      if (_activeBadge) { _activeBadge.removeAttribute('aria-describedby'); _activeBadge = null; }
    }
    function showTip(badge) {
      var raw = badge.getAttribute('data-tip') || '';
      if (!raw) { hideTip(); return; }
      var lines = raw.split('\n');
      while (tip.firstChild) tip.removeChild(tip.firstChild);
      var head = document.createElement('b');
      head.className = 'tip-head';
      head.textContent = lines[0];
      tip.appendChild(head);
      for (var i = 1; i < lines.length; i++) {
        var row = document.createElement('span');
        row.className = 'tip-row';
        row.textContent = lines[i];
        tip.appendChild(row);
      }
      tip.hidden = false;
      _activeBadge = badge;
      var r = badge.getBoundingClientRect();
      var tw = tip.offsetWidth, th = tip.offsetHeight, vw = document.documentElement.clientWidth, vh = window.innerHeight, m = 6;
      var left = Math.min(r.right - tw, vw - tw - m); if (left < m) left = m;
      var top = r.bottom + m; if (top + th > vh - m) top = Math.max(m, r.top - th - m);
      tip.style.left = left + 'px'; tip.style.top = top + 'px';
      badge.setAttribute('aria-describedby', 'tier-tip');
    }
    document.addEventListener('pointerover', function (e) {
      var b = e.target.closest && e.target.closest('[data-tip]');
      if (b) showTip(b); else if (!tip.hidden) hideTip();
    });
    document.addEventListener('focusin', function (e) {
      var b = e.target.closest && e.target.closest('[data-tip]');
      if (b) showTip(b); else if (!tip.hidden) hideTip();
    });
    document.addEventListener('focusout', function (e) { if (e.target.closest && e.target.closest('[data-tip]')) hideTip(); });
    window.addEventListener('scroll', function () { if (!tip.hidden) hideTip(); }, { passive: true });
    window.addEventListener('resize', function () { if (!tip.hidden) hideTip(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !tip.hidden) hideTip(); });
  }

  // (2b1) Statute-jump dropdown on /statute/ - selecting a section sets the
  //       URL hash, which the openDetailsFor handler at (1) auto-opens.
  var statSel = document.getElementById('statute-jump');
  if (statSel) {
    // Reveal the jump bar only once JS can wire it; without JS the <select>
    // does nothing, so it ships hidden (sections stay reachable by scroll).
    var statBar = document.getElementById('statute-jump-bar');
    if (statBar) statBar.hidden = false;
    statSel.addEventListener('change', function () {
      var v = statSel.value;
      if (v) location.hash = '#' + v;
    });
  }

  // (2c) Roster view toggle - flip month cards between grid and table-like list.
  var vt = document.getElementById('view-toggle');
  if (vt) {
    vt.hidden = false;
    var saved = null;
    try { saved = localStorage.getItem('jcs-view'); } catch (e) {}
    if (saved === 'table') document.body.classList.add('is-table');
    function syncToggle() {
      var on = document.body.classList.contains('is-table');
      vt.setAttribute('aria-pressed', on ? 'true' : 'false');
      var txt = vt.querySelector('.view-toggle-text');
      if (txt) txt.textContent = on ? 'Card view' : 'Table view';
    }
    vt.addEventListener('click', function () {
      document.body.classList.toggle('is-table');
      try { localStorage.setItem('jcs-view', document.body.classList.contains('is-table') ? 'table' : 'cards'); } catch (e) {}
      syncToggle();
    });
    syncToggle();
  }

  // (3) Filter bar. Scoped to its own block so a page without #filters still
  //     reaches the (4) search dropdown below, which is an independent feature.
  var bar = document.getElementById('filters');
  if (bar && bar.hasAttribute('data-roster-preview')) {
    // The preview is deliberately bounded. Never filter only those 48 cards
    // and claim the rest of the custody roster has no matches.
    if (location.search || /^#m-/.test(location.hash)) {
      location.replace(ROOT + '/archive/' + location.search + location.hash);
    }
    bar.querySelectorAll('select[data-filter]').forEach(function (select) {
      select.addEventListener('change', function () { bar.requestSubmit(); });
    });
    var previewSort = document.getElementById('filter-sort');
    if (previewSort) previewSort.addEventListener('change', function () {
      location.href = ROOT + '/archive/?sort=' + encodeURIComponent(previewSort.value);
    });
  }
  if (bar && !bar.hasAttribute('data-roster-preview')) {
    bar.addEventListener('submit', function (event) { event.preventDefault(); apply('search'); });
    var submitButton = bar.querySelector('.roster-submit');
    if (submitButton) submitButton.hidden = true;
    bar.hidden = false;
    var inputs = bar.querySelectorAll('[data-filter]');
    var countEl = bar.querySelector('.filter-count');
    var noMatch = bar.parentNode.querySelector('#filter-empty');
    var resetBtn = document.getElementById('filter-reset');
    var cards = Array.prototype.slice.call(document.querySelectorAll('.cards .card-inmate'));
    var months = Array.prototype.slice.call(document.querySelectorAll('details.month'));
    var DEG_VALUES = { f1: 1, f2: 1, f3: 1, f4: 1, f5: 1, m1: 1, m2: 1, m3: 1, m4: 1, mm: 1 };
    function currentFilters() {
      var f = {};
      inputs.forEach(function (i) { f[i.getAttribute('data-filter')] = (i.value || '').trim().toLowerCase(); });
      return f;
    }
    function matchesCard(c, f) {
      if (f.tier) {
        if (DEG_VALUES[f.tier]) {
          if (c.getAttribute('data-degree') !== f.tier.toUpperCase()) return false;
        } else if (c.getAttribute('data-tier') !== f.tier) {
          return false;
        }
      }
      if (f.chap && c.getAttribute('data-chap') !== f.chap) return false;
      if (f.recent && c.getAttribute('data-recent') !== f.recent) return false;
      if (f.search && (c.getAttribute('data-search') || '').indexOf(f.search) === -1) return false;
      return true;
    }
    function syncUrl(f) {
      if (!window.history || !window.history.replaceState) return;
      var sp = new URLSearchParams();
      if (f.search) sp.set('q', f.search);
      if (f.tier) sp.set('tier', f.tier);
      if (f.chap) sp.set('chap', f.chap);
      if (f.recent) sp.set('recent', f.recent);
      var sort = document.getElementById('filter-sort');
      if (sort && sort.value !== 'recent') sp.set('sort', sort.value);
      if (pagerSize !== 24) sp.set('pagesize', String(pagerSize));
      // The page param tracks the primary (first visible) paginated list so
      // a copied URL restores the page the reader was on.
      var prim = primaryContainer();
      if (prim) {
        var primPage = pagerPages[prim.id] || 1;
        if (primPage > 1) sp.set('page', String(primPage));
      }
      var qs = sp.toString();
      var hash = window.location.hash || '';
      var next = window.location.pathname + (qs ? '?' + qs : '') + hash;
      var cur = window.location.pathname + window.location.search + window.location.hash;
      if (next !== cur) window.history.replaceState({}, '', next);
    }
    function recountFilterOptions(f) {
      function recount(sel, skipKey) {
        if (!sel) return;
        Array.prototype.forEach.call(sel.options, function (opt) {
          if (!opt.value) return;
          if (!opt.dataset.label) {
            opt.dataset.label = opt.textContent.replace(/\s*\(\d+\)\s*$/, '');
          }
          var f2 = { tier: f.tier, chap: f.chap, recent: f.recent, search: f.search };
          f2[skipKey] = opt.value;
          var n = 0;
          for (var i = 0; i < cards.length; i++) {
            if (matchesCard(cards[i], f2)) n++;
          }
          opt.textContent = opt.dataset.label + ' (' + n + ')';
        });
      }
      recount(bar.querySelector('[data-filter="chap"]'), 'chap');
      recount(bar.querySelector('[data-filter="tier"]'), 'tier');
    }
    // Search-match emphasis: wrap each occurrence of the term in the card's
    // visible text in <mark class="hl">. Text-node splitting via DOM APIs
    // only - no innerHTML (same CodeQL js/xss-through-dom discipline as the
    // dropdown below). Skipped for 1-char terms: single-letter searches match
    // most of the roster and marking every letter is noise, not signal.
    function clearAllMarks() {
      // One global query instead of per-card queries: only cards that
      // actually contain marks (bounded by the previous match count) pay
      // for cleanup and normalize().
      var marks = document.querySelectorAll('.cards mark.hl');
      var touched = [];
      for (var i = 0; i < marks.length; i++) {
        var m = marks[i];
        var card = m.closest('.card-inmate');
        m.parentNode.replaceChild(document.createTextNode(m.textContent), m);
        if (card && touched.indexOf(card) === -1) touched.push(card);
      }
      for (var j = 0; j < touched.length; j++) touched[j].normalize();
    }
    function markTerm(card, term) {
      var roots = card.querySelectorAll('.name a, .charge, .id-chip');
      for (var i = 0; i < roots.length; i++) {
        var walker = document.createTreeWalker(roots[i], NodeFilter.SHOW_TEXT);
        var textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);
        textNodes.forEach(function (tn) {
          var text = tn.nodeValue;
          var at = text.toLowerCase().indexOf(term);
          if (at === -1) return;
          var frag = document.createDocumentFragment();
          var pos = 0;
          while (at !== -1) {
            if (at > pos) frag.appendChild(document.createTextNode(text.slice(pos, at)));
            var mk = document.createElement('mark');
            mk.className = 'hl';
            mk.textContent = text.slice(at, at + term.length);
            frag.appendChild(mk);
            pos = at + term.length;
            at = text.toLowerCase().indexOf(term, pos);
          }
          if (pos < text.length) frag.appendChild(document.createTextNode(text.slice(pos)));
          tn.parentNode.replaceChild(frag, tn);
        });
      }
    }
    function apply(trigger) {
      var f = currentFilters();
      if (trigger !== 'init') {
        // Any new filter or sort input restarts every paginated list at
        // page 1; the URL page param is dropped by syncUrl below.
        pagerPages = {};
      }
      var active = !!(f.tier || f.chap || f.search || f.recent);
      var shown = 0;
      clearAllMarks();
      cards.forEach(function (c) {
        var ok = matchesCard(c, f);
        c.classList.toggle('is-filtered-out', !ok);
        if (ok) shown++;
        if (ok && f.search && f.search.length >= 2) markTerm(c, f.search);
      });
      months.forEach(function (m) {
        var anyVisible = m.querySelector('.card-inmate:not(.is-filtered-out)');
        m.classList.toggle('is-empty', !anyVisible && active);
        if (active && anyVisible) m.open = true;
      });
      if (noMatch) noMatch.hidden = !(active && shown === 0);
      // Restate the active filters next to the count so the user never has
      // to reconstruct "what did I click" from three separate controls.
      var pieces = [];
      if (f.search) pieces.push('matching "' + f.search + '"');
      if (f.chap) {
        var chapOptSel = bar.querySelector('[data-filter="chap"]');
        var chapOpt = chapOptSel && chapOptSel.options[chapOptSel.selectedIndex];
        if (chapOpt) pieces.push('offense: ' + chapOpt.textContent.replace(/\s*\(\d+\)$/, ''));
      }
      if (f.tier) pieces.push(DEG_VALUES[f.tier] ? 'degree: ' + f.tier.toUpperCase() : 'tier: ' + f.tier);
      if (f.recent) pieces.push('booked in last 24h');
      var summary = shown + ' of ' + cards.length + ' shown' + (pieces.length ? ' · ' + pieces.join(' · ') : '');
      countEl.textContent = active ? summary : '';
      if (resetBtn) resetBtn.hidden = !active;
      // Single-announcer rule: select changes announce the card count here;
      // search keystrokes are announced by the dropdown's own result count
      // (section 4), never both for one event.
      var status = document.getElementById('search-status');
      if (status && trigger !== 'search') {
        status.textContent = active ? summary : '';
      }
      recountFilterOptions(f);
      renderPagination();
      if (trigger !== 'init') syncUrl(f);
    }

    // (3d) Pagination. Each month (and the sort-bin) is an independent
    //      paginated list: 24 cards per page default, 24/48/96 choices.
    //      Paginates the filtered set within each visible container, so it
    //      composes with search/tier/offense/activity filters and sort modes.
    //      Pager navs are built by JS only: without JS every card renders and
    //      there is no paging (progressive enhancement).
    var PAGE_SIZES = [24, 48, 96];
    var pagerSize = 24;
    var pagerPages = {}; // container id -> current page, 1-based
    function mkEl(tag, cls) {
      var e = document.createElement(tag);
      if (cls) e.className = cls;
      return e;
    }
    function pagerSortBin() { return document.getElementById('sort-bin'); }
    function pagerContainers() {
      // Visible paginated lists in DOM order: the sort-bin when a sort mode
      // is active, otherwise every open, non-hidden month. Closed months
      // are excluded: their pagers are not visible, and opening one starts
      // it at page 1 via the toggle handler below. Hidden months (sort
      // mode) are excluded; filter-emptied months render zero cards and
      // their pagers hide themselves.
      var list = [];
      var sb = pagerSortBin();
      if (sb && !sb.hidden) list.push(sb);
      months.forEach(function (m) { if (!m.hidden && m.open) list.push(m); });
      return list;
    }
    function primaryContainer() {
      var cs = pagerContainers();
      return cs.length ? cs[0] : null;
    }
    function filteredList(container) {
      var out = [];
      var all = container.querySelectorAll('.cards .card-inmate');
      for (var i = 0; i < all.length; i++) {
        if (!all[i].classList.contains('is-filtered-out')) out.push(all[i]);
      }
      return out;
    }
    function totalPagesFor(n) { return Math.max(1, Math.ceil(n / pagerSize)); }
    function pageOf(id, total) {
      var p = pagerPages[id] || 1;
      if (p < 1) p = 1;
      if (p > total) p = total;
      pagerPages[id] = p;
      return p;
    }
    function pagerLabel(container) {
      var h = container.querySelector('summary h2');
      if (h) return h.textContent.trim();
      return container.getAttribute('aria-label') || 'roster';
    }
    function pageWindow(page, total) {
      // Numbered buttons: first, last, and one neighbor each side of the
      // current page, with ellipses for gaps. AUDHD-friendly: never a wall
      // of tiny numbers; prev/next + first/last always present.
      var out = [];
      [1, page - 1, page, page + 1, total].forEach(function (p) {
        if (p >= 1 && p <= total && out.indexOf(p) === -1) out.push(p);
      });
      out.sort(function (a, b) { return a - b; });
      return out;
    }
    function renderPagerNav(container, pos, st) {
      var nav = mkEl('nav', 'pager pager-' + pos);
      nav.setAttribute('aria-label', 'Roster pages, ' + st.label);
      var ctrls = mkEl('div', 'pager-controls');
      var btns = mkEl('div', 'pager-btns');
      function pgBtn(text, pg, alabel, disabled) {
        var b = mkEl('button', 'pager-btn');
        b.type = 'button';
        b.setAttribute('data-pg', pg);
        b.setAttribute('data-container', container.id);
        b.textContent = text;
        b.setAttribute('aria-label', alabel);
        if (disabled) b.disabled = true;
        return b;
      }
      btns.appendChild(pgBtn('First', 'first', 'First page, ' + st.label, st.page <= 1));
      btns.appendChild(pgBtn('Prev', 'prev', 'Previous page, ' + st.label, st.page <= 1));
      var nums = mkEl('span', 'pager-nums');
      nums.setAttribute('role', 'group');
      nums.setAttribute('aria-label', 'Page numbers, ' + st.label);
      var win = pageWindow(st.page, st.total);
      var prevP = 0;
      win.forEach(function (p) {
        if (p - prevP > 1) {
          var ell = mkEl('span', 'pager-ellipsis');
          ell.textContent = '…';
          ell.setAttribute('aria-hidden', 'true');
          nums.appendChild(ell);
        }
        var nb = mkEl('button', 'pager-num');
        nb.type = 'button';
        nb.setAttribute('data-pg', String(p));
        nb.setAttribute('data-container', container.id);
        nb.textContent = String(p);
        if (p === st.page) {
          nb.setAttribute('aria-current', 'page');
          nb.setAttribute('aria-label', 'Page ' + p + ', current page, ' + st.label);
        } else {
          nb.setAttribute('aria-label', 'Go to page ' + p + ', ' + st.label);
        }
        nums.appendChild(nb);
        prevP = p;
      });
      btns.appendChild(nums);
      btns.appendChild(pgBtn('Next', 'next', 'Next page, ' + st.label, st.page >= st.total));
      btns.appendChild(pgBtn('Last', 'last', 'Last page, ' + st.label, st.page >= st.total));
      ctrls.appendChild(btns);
      // Count line: the bottom nav's full status is the polite live region
      // so page changes are announced once; it is the only pager now.
      var status = mkEl('p', 'pager-status');
      var compact = mkEl('span', 'pager-status-compact');
      compact.textContent = 'Page ' + st.page + ' of ' + st.total;
      var full = mkEl('span', 'pager-status-full');
      var range = st.count > 0 ? (st.start + 1) + '-' + st.end + ' of ' + st.count : '0 of 0';
      full.textContent = 'Page ' + st.page + ' of ' + st.total + ' · Showing ' + range;
      if (pos === 'bottom') full.setAttribute('aria-live', 'polite');
      status.appendChild(compact);
      status.appendChild(document.createTextNode(' '));
      status.appendChild(full);
      ctrls.appendChild(status);
      var sizeLab = mkEl('label', 'pager-size');
      sizeLab.appendChild(document.createTextNode('Per page '));
      var sel = document.createElement('select');
      sel.className = 'pager-size-sel';
      sel.setAttribute('data-container', container.id);
      sel.setAttribute('aria-label', 'Cards per page, ' + st.label);
      PAGE_SIZES.forEach(function (s) {
        var o = document.createElement('option');
        o.value = String(s);
        o.textContent = String(s);
        if (s === pagerSize) o.selected = true;
        sel.appendChild(o);
      });
      sizeLab.appendChild(sel);
      ctrls.appendChild(sizeLab);
      nav.appendChild(ctrls);
      return nav;
    }
    function renderPagination() {
      pagerContainers().forEach(function (container) {
        var list = filteredList(container);
        var total = totalPagesFor(list.length);
        var page = pageOf(container.id, total);
        var start = (page - 1) * pagerSize;
        var end = Math.min(start + pagerSize, list.length);
        var all = container.querySelectorAll('.cards .card-inmate');
        var i;
        for (i = 0; i < all.length; i++) all[i].classList.remove('is-paged-out');
        for (i = 0; i < list.length; i++) {
          if (i < start || i >= end) list[i].classList.add('is-paged-out');
        }
        // Rebuild the below-list pager from current state. It only
        // exists while JS runs, so no-JS keeps the full unpaged list.
        // The roster always renders before the pager (owner-directed).
        for (i = container.children.length - 1; i >= 0; i--) {
          var ch = container.children[i];
          if (ch.classList && ch.classList.contains('pager')) container.removeChild(ch);
        }
        if (total > 1) {
          var cardsEl = container.querySelector('.cards');
          var st = { label: pagerLabel(container), page: page, total: total,
                     start: start, end: end, count: list.length };
          if (cardsEl.nextSibling) container.insertBefore(renderPagerNav(container, 'bottom', st), cardsEl.nextSibling);
          else container.appendChild(renderPagerNav(container, 'bottom', st));
        }
      });
    }
    function focusListTop(container) {
      // Page change moves context to the list top: AT focus without a
      // scroll jump, then a smooth (or instant, under reduced-motion)
      // scroll of the container into view. The .month scroll-margin-top
      // keeps the sticky masthead clear of the heading.
      var h2 = container.querySelector('summary h2');
      var target = h2 || container.querySelector('nav.pager');
      if (target) {
        target.tabIndex = -1;
        try { target.focus({ preventScroll: true }); }
        catch (err) { try { target.focus(); } catch (e2) {} }
      }
      var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      try { container.scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' }); }
      catch (err) {}
    }
    // Pager button activation (delegated; navs are rebuilt on every render).
    document.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest ? e.target.closest('.pager [data-pg]') : null;
      if (!btn || btn.disabled) return;
      var container = document.getElementById(btn.getAttribute('data-container'));
      if (!container) return;
      var list = filteredList(container);
      var total = totalPagesFor(list.length);
      var page = pagerPages[container.id] || 1;
      var pg = btn.getAttribute('data-pg');
      var next = pg === 'first' ? 1 : pg === 'prev' ? page - 1 :
                 pg === 'next' ? page + 1 : pg === 'last' ? total :
                 (parseInt(pg, 10) || 1);
      if (next < 1) next = 1;
      if (next > total) next = total;
      if (next === page) return;
      pagerPages[container.id] = next;
      renderPagination();
      syncUrl(currentFilters());
      focusListTop(container);
    });
    // Page-size change (delegated): new size restarts at page 1 everywhere.
    document.addEventListener('change', function (e) {
      var sel = e.target && e.target.closest ? e.target.closest('.pager-size-sel') : null;
      if (!sel) return;
      var s = parseInt(sel.value, 10);
      if (PAGE_SIZES.indexOf(s) === -1 || s === pagerSize) return;
      pagerSize = s;
      pagerPages = {};
      renderPagination();
      syncUrl(currentFilters());
    });
    // Opening a month starts it at page 1 and builds its pagers; closing
    // one (or opening another) can change which list the ?page= param
    // tracks, so re-sync the URL on every toggle.
    months.forEach(function (m) {
      var wasOpen = m.open;
      m.addEventListener('toggle', function () {
        if (m.open === wasOpen) return; // Ignore initial markup's queued toggle.
        wasOpen = m.open;
        if (m.open) {
          pagerPages[m.id] = 1;
          renderPagination();
        }
        syncUrl(currentFilters());
      });
    });
    var applyDebounce = null;
    inputs.forEach(function (i) {
      var key = i.getAttribute('data-filter');
      function run() { apply(key); }
      i.addEventListener('input', key === 'search' ? function () {
        // Debounce typing so 1268 cards aren't re-filtered per keystroke.
        clearTimeout(applyDebounce);
        applyDebounce = setTimeout(run, 200);
      } : run);
      i.addEventListener('change', run);
    });
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        clearTimeout(applyDebounce);
        inputs.forEach(function (i) { i.value = ''; });
        if (window.history && window.history.replaceState) {
          window.history.replaceState({}, '', window.location.pathname);
        }
        apply('reset');
        months.forEach(function (m, idx) {
          m.open = (idx === 0);
        });
        var searchResults = document.getElementById('search-results');
        if (searchResults) searchResults.hidden = true;
        var status = document.getElementById('search-status');
        if (status) status.textContent = 'Filters reset';
        var search = document.getElementById('search-box');
        if (search && search.focus) search.focus();
      });
    }

    // Deep-link: ?chap=... / ?tier=... (e.g. from the stats offense-category
    // links) pre-applies the matching filter so the link lands on a filtered
    // roster. Only sets a value the corresponding <select> actually offers.
    try {
      var params = new URLSearchParams(location.search);
      inputs.forEach(function (i) {
        var key = i.getAttribute('data-filter');
        var val = (params.get(key) || '').trim();
        if (key === 'search' && !val) val = (params.get('q') || '').trim();
        val = val.toLowerCase();
        if (!val) return;
        if (i.tagName === 'SELECT') {
          var ok = Array.prototype.some.call(i.options, function (o) { return o.value === val; });
          if (!ok) return;
        }
        i.value = val;
      });
      // Pager deep-link: ?pagesize= (24/48/96) applies globally; ?page=
      // seeds the primary (first visible) paginated list. renderPagination
      // inside apply('init') clamps it to the real page count.
      var psz = parseInt(params.get('pagesize') || '', 10);
      if (PAGE_SIZES.indexOf(psz) !== -1) pagerSize = psz;
      var pnum = parseInt(params.get('page') || '', 10);
      if (pnum > 1) {
        var primInit = primaryContainer();
        if (primInit) pagerPages[primInit.id] = pnum;
      }
    } catch (e) {}
    apply('init');

    // (3b) Crime-of-month pills: click to filter roster by that chapter.
    var chapSelect = document.getElementById('filter-chap');
    if (chapSelect) {
      document.addEventListener('click', function (e) {
        var pill = e.target.closest('.coms .chap');
        if (!pill) return;
        var cls = '';
        pill.classList.forEach(function (c) { if (c.indexOf('chap-') === 0) cls = c.replace('chap-', ''); });
        if (!cls) return;
        chapSelect.value = cls;
        chapSelect.dispatchEvent(new Event('change'));
        var scrollBehavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
        bar.scrollIntoView({ block: 'start', behavior: scrollBehavior });
      });
    }
    // (3c) Sort modes - non-default modes move every card into the flat
    //      #sort-bin in sorted order and hide the month sections; "recent"
    //      moves each card back to its original month container (appending
    //      in original global order preserves within-month order). Filters
    //      keep working either way: they only toggle is-filtered-out.
    var sortSel = document.getElementById('filter-sort');
    var sortBin = document.getElementById('sort-bin');
    if (sortSel && sortBin) {
      var binCards = sortBin.querySelector('.cards');
      var origins = cards.map(function (c) { return c.parentNode; });
      // Bare F / M come from venue inference (no numbered degree); rank them
      // below their numbered ladder so unknown-degree felonies sort after F5.
      var degRank = { F1: 1, F2: 2, F3: 3, F4: 4, F5: 5, F: 6, M1: 7, M2: 8, M3: 9, M4: 10, MM: 11, M: 12 };
      sortSel.addEventListener('change', function () {
        var mode = sortSel.value;
        if (mode === 'recent') {
          cards.forEach(function (c, i) { origins[i].appendChild(c); });
          sortBin.hidden = true;
          months.forEach(function (m) { m.hidden = false; });
          // Recompute month is-empty/open states - they went stale while the
          // months were empty (any apply() during sorted mode saw no cards).
          apply('sort');
          return;
        }
        var order = cards.slice().sort(function (a, b) {
          if (mode === 'custody') {
            return Number(b.getAttribute('data-custody') || -1) - Number(a.getAttribute('data-custody') || -1);
          }
          if (mode === 'degree') {
            return (degRank[a.getAttribute('data-degree')] || 99) - (degRank[b.getAttribute('data-degree')] || 99);
          }
          // name: data-search starts with the lowercased full name.
          return (a.getAttribute('data-search') || '').localeCompare(b.getAttribute('data-search') || '');
        });
        var frag = document.createDocumentFragment();
        order.forEach(function (c) { frag.appendChild(c); });
        binCards.appendChild(frag);
        months.forEach(function (m) { m.hidden = true; });
        sortBin.hidden = false;
        // New card order: restart the sort-bin pager at page 1.
        pagerPages = {};
        renderPagination();
        syncUrl(currentFilters());
      });
      var requestedSort = new URLSearchParams(location.search).get('sort');
      if (['custody', 'degree', 'name'].indexOf(requestedSort) !== -1) {
        sortSel.value = requestedSort;
        sortSel.dispatchEvent(new Event('change'));
        // Sorting resets interactive pagination. Restore a requested URL page
        // after the initial sort has moved cards into the active container.
        if (pnum > 1) {
          pagerPages[sortBin.id] = pnum;
          renderPagination();
          syncUrl(currentFilters());
        }
      }
    }
  } // end (3) filter bar

  // (4) Search-results dropdown - lazy-loads search.json on first keystroke,
  //     shows a type-ahead list of matching people. Uses DOM APIs (not innerHTML)
  //     to satisfy CodeQL DOM-text-reinterpreted-as-HTML checks.
  var sbox = document.getElementById('search-box');
  var sresults = document.getElementById('search-results');
  var sstatus = document.getElementById('search-status');
  if (sbox && sresults) {
    var idx = null, loading = false;
    function loadIdx() {
      if (idx || loading) return;
      loading = true;
      fetch(ROOT + '/search.json').then(function (r) {
        if (!r.ok) throw new Error('Search index unavailable');
        return r.json();
      })
        .then(function (d) { idx = (d && d.rows) || []; render(); })
        .catch(function () {
          loading = false;
          if (sstatus) sstatus.textContent = 'Search suggestions unavailable. Use Search all or browse the full roster archive.';
        });
    }
    function clearEl(el) { while (el.firstChild) el.removeChild(el.firstChild); }
    function render() {
      var q = (sbox.value || '').trim().toLowerCase();
      if (!q || q.length < 2 || !idx) {
        sresults.hidden = true;
        if (sstatus) sstatus.textContent = '';
        return;
      }
      var hits = [];
      for (var i = 0; i < idx.length && hits.length < 20; i++) {
        var r = idx[i];
        if ((r.s || (r.n + ' ' + r.c + ' #' + r.id)).toLowerCase().indexOf(q) !== -1) hits.push(r);
      }
      clearEl(sresults);
      if (!hits.length) {
        var empty = document.createElement('div');
        empty.className = 'sr-empty';
        empty.textContent = 'No one matches "' + q + '".';
        sresults.appendChild(empty);
      } else {
        hits.forEach(function (r) {
          var a = document.createElement('a');
          a.className = 'sr-item';
          a.href = ROOT + '/inmate/' + r.id + '/';
          var tierSpan = document.createElement('span');
          tierSpan.className = 'sr-tier sr-' + (r.t || 'x');
          tierSpan.textContent = r.t === 'felony' ? 'F' : r.t === 'misdemeanor' ? 'M' : '?';
          a.appendChild(tierSpan);
          var nameSpan = document.createElement('span');
          nameSpan.className = 'sr-name';
          nameSpan.textContent = r.n;
          a.appendChild(nameSpan);
          var chargeSpan = document.createElement('span');
          chargeSpan.className = 'sr-charge';
          chargeSpan.textContent = r.c;
          a.appendChild(chargeSpan);
          sresults.appendChild(a);
        });
      }
      sresults.hidden = false;
      // Announce a count via the sr-only status node instead of making the
      // whole re-rendered list a live region (verbose in some screen readers).
      if (sstatus) {
        sstatus.textContent = hits.length
          ? hits.length + (hits.length === 1 ? ' result' : ' results')
          : 'No results';
      }
    }
    function dismiss() {
      sresults.hidden = true;
      if (sstatus) sstatus.textContent = '';
    }
    // (4b) "/" focuses the roster search from anywhere on the page, unless
    //      the user is already typing in a form control.
    document.addEventListener('keydown', function (e) {
      if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
      e.preventDefault();
      sbox.focus();
    });
    var renderDebounce = null;
    sbox.addEventListener('focus', loadIdx);
    sbox.addEventListener('input', function () {
      loadIdx();
      clearTimeout(renderDebounce);
      renderDebounce = setTimeout(render, 200);
    });
    sbox.addEventListener('keydown', function (e) { if (e.key === 'Escape') dismiss(); });
    document.addEventListener('click', function (e) {
      if (!sresults.contains(e.target) && e.target !== sbox) dismiss();
    });
  }

  // (N) Theme toggle: theme-init.js sets the initial data-theme pre-paint;
  //     this only handles clicks. Choice persists in localStorage.
  var themeBtn = document.querySelector('.theme-toggle');
  if (themeBtn) {
    var metaTheme = document.querySelector('meta[name="theme-color"]');
    var syncThemeMeta = function () {
      if (metaTheme) metaTheme.setAttribute('content',
        document.documentElement.getAttribute('data-theme') === 'light' ? '#F5F0EB' : '#141619');
    };
    /* aria-pressed mirrors the toggle state for assistive tech:
       pressed = dark theme active. Synced here (deferred) and on click;
       theme-init.js can't set it pre-paint because <body> isn't parsed yet. */
    var syncThemePressed = function () {
      themeBtn.setAttribute('aria-pressed',
        document.documentElement.getAttribute('data-theme') === 'light' ? 'false' : 'true');
    };
    syncThemeMeta();
    syncThemePressed();
    themeBtn.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('jcstream-theme', next); } catch (e) { /* ignore */ }
      syncThemeMeta();
      syncThemePressed();
    });
  }

  // (O) Booking-photo graceful degradation (V8-F1/V9-L01). Inline onerror is
  //     blocked by the CSP (script-src 'self', no 'unsafe-inline'), so failed
  //     booking photos are handled here: a capture-phase error listener for
  //     failures after this deferred bundle runs, plus a sweep for images
  //     that already failed before it ran. Each context mirrors the
  //     placeholder its template renders when no photo filename exists.
  (function photoFallback() {
    function initialsFor(img, fallbackEl) {
      return img.getAttribute("data-initials")
        || (fallbackEl && fallbackEl.getAttribute("data-initials"))
        || "?";
    }
    function swapPhoto(img) {
      if (!img || img.getAttribute("data-photo-fallback-done")) return;
      img.setAttribute("data-photo-fallback-done", "1");
      // Inmate hero figure: rebuild the no-photo placeholder.
      var figure = img.closest("figure.record-photo");
      if (figure) {
        var link = img.closest("a");
        if (link) link.remove();
        var hero = document.createElement("span");
        hero.className = "thumb thumb-placeholder thumb-hero";
        hero.setAttribute("aria-hidden", "true");
        hero.setAttribute("data-initials", figure.getAttribute("data-initials") || "?");
        figure.insertBefore(hero, figure.firstChild);
        var cap = figure.querySelector("figcaption");
        if (cap) cap.textContent = "No booking photo on file";
        return;
      }
      // Related-booking / statute held-inmate thumbnails.
      var rb = img.closest(".rb-photo");
      if (rb) {
        rb.classList.add("is-placeholder");
        rb.setAttribute("data-initials", initialsFor(img, rb));
        img.remove();
        return;
      }
      // Court page cards.
      var cc = img.closest(".court-card-photo");
      if (cc) {
        cc.classList.add("court-card-photo-placeholder");
        cc.setAttribute("data-initials", initialsFor(img, cc));
        img.remove();
        return;
      }
      // Homepage cards: the anchor itself is the .thumb; replace it with the
      // placeholder span the no-photo branch renders.
      var cardAnchor = img.closest("a.thumb");
      if (cardAnchor) {
        var s = document.createElement("span");
        s.className = "thumb thumb-placeholder";
        s.setAttribute("aria-hidden", "true");
        s.setAttribute("data-initials", initialsFor(img, cardAnchor));
        cardAnchor.replaceWith(s);
        return;
      }
      img.style.display = "none";
    }
    document.addEventListener("error", function (e) {
      var t = e.target;
      if (t && t.tagName === "IMG" && t.hasAttribute("data-photo-fallback")) swapPhoto(t);
    }, true);
    function sweep() {
      var imgs = document.querySelectorAll("img[data-photo-fallback]");
      for (var i = 0; i < imgs.length; i++) {
        var im = imgs[i];
        if (im.complete && im.naturalWidth === 0) swapPhoto(im);
      }
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", sweep);
    else sweep();
  })();
})();
