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
    setTimeout(function () { el.scrollIntoView({ block: 'start', behavior: 'auto' }); }, 0);
  }
  window.addEventListener('hashchange', function () { openDetailsFor(location.hash); });
  if (location.hash) openDetailsFor(location.hash);
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="#"]');
    if (a && a.getAttribute('href').length > 1) openDetailsFor(a.getAttribute('href'));
  });

  // (1b) Site nav drawer. Markup ships with [open] so the no-JS fallback is
  // an expanded (usable) list; with JS, small screens start closed and the
  // drawer dismisses on outside click. Desktop hides the toggle entirely.
  var navMenu = document.querySelector('.nav-menu');
  if (navMenu && window.matchMedia) {
    var navMQ = window.matchMedia('(max-width: 720px)');
    if (navMQ.matches) navMenu.removeAttribute('open');
    document.addEventListener('click', function (e) {
      if (navMQ.matches && navMenu.open && !navMenu.contains(e.target)) navMenu.removeAttribute('open');
    });
  }

  // (2) Shared lightbox.
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
    lb.hidden = true; lbImg.src = '';
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
  if (bar) {
    bar.hidden = false;
    var inputs = bar.querySelectorAll('[data-filter]');
    var countEl = bar.querySelector('.filter-count');
    var noMatch = bar.parentNode.querySelector('#filter-empty');
    var resetBtn = document.getElementById('filter-reset');
    var cards = Array.prototype.slice.call(document.querySelectorAll('.cards .card-inmate'));
    var months = Array.prototype.slice.call(document.querySelectorAll('details.month'));
    function currentFilters() {
      var f = {};
      inputs.forEach(function (i) { f[i.getAttribute('data-filter')] = (i.value || '').trim().toLowerCase(); });
      return f;
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
      var active = !!(f.tier || f.chap || f.search);
      var shown = 0;
      clearAllMarks();
      cards.forEach(function (c) {
        var ok = true;
        if (f.tier && c.getAttribute('data-tier') !== f.tier) ok = false;
        if (ok && f.chap && c.getAttribute('data-chap') !== f.chap) ok = false;
        if (ok && f.search && (c.getAttribute('data-search') || '').indexOf(f.search) === -1) ok = false;
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
      if (f.tier) pieces.push('tier: ' + f.tier);
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
    }
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
        var val = (params.get(key) || '').trim().toLowerCase();
        if (!val) return;
        if (i.tagName === 'SELECT') {
          var ok = Array.prototype.some.call(i.options, function (o) { return o.value === val; });
          if (!ok) return;
        }
        i.value = val;
      });
    } catch (e) {}
    apply();

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
      fetch(ROOT + '/search.json').then(function (r) { return r.json(); })
        .then(function (d) { idx = (d && d.rows) || []; render(); })
        .catch(function () { idx = []; });
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
        if ((r.n + ' ' + r.c + ' #' + r.id).toLowerCase().indexOf(q) !== -1) hits.push(r);
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
})();
