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

  // (2) Shared lightbox.
  var lb = document.getElementById('lb');
  var lbImg = document.getElementById('lb-img');
  var lbCap = document.getElementById('lb-cap');
  var lastFocus = null;
  function openLB(src, caption) {
    lastFocus = document.activeElement;
    // src comes from a [data-photo] DOM attribute. Validate it's a same-origin
    // .jpg path before assigning to .src, both to neutralize the CodeQL
    // js/xss-through-dom flow and to refuse anything that isn't a booking
    // photo (javascript: URLs, protocol-relative //host/x, off-origin https://).
    // Accepts /photos/123.jpg and /<base_url>/photos/123.jpg; rejects //host/...
    if (typeof src !== 'string' || src.charAt(0) !== '/' || src.indexOf('//') !== -1 || !/\.jpg$/i.test(src)) return;
    lbImg.src = src;
    lbImg.alt = 'Booking photo';
    lbCap.textContent = caption || '';
    lb.hidden = false;
    // Confine focus to the dialog: mark all other body children inert.
    // Browsers without inert support fall back to the Tab cycler below.
    Array.prototype.forEach.call(document.body.children, function (n) {
      if (n !== lb) n.inert = true;
    });
    lb.querySelector('.lightbox-close').focus();
  }
  function closeLB() {
    lb.hidden = true; lbImg.src = '';
    Array.prototype.forEach.call(document.body.children, function (n) {
      n.inert = false;
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
    e.preventDefault();
    openLB(t.getAttribute('data-photo'), t.getAttribute('data-photo-cap'));
  });

  // (2b) Shared tier-badge tooltip - content lives in [data-tip], JS positions it.
  //      Uses DOM APIs (not innerHTML) to avoid CodeQL DOM-text-reinterpreted-as-HTML.
  var tip = document.getElementById('tier-tip');
  if (tip) {
    function hideTip() { tip.hidden = true; tip.style.left = '-9999px'; }
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
      var r = badge.getBoundingClientRect();
      var tw = tip.offsetWidth, th = tip.offsetHeight, vw = document.documentElement.clientWidth, vh = window.innerHeight, m = 6;
      var left = Math.min(r.right - tw, vw - tw - m); if (left < m) left = m;
      var top = r.bottom + m; if (top + th > vh - m) top = Math.max(m, r.top - th - m);
      tip.style.left = left + 'px'; tip.style.top = top + 'px';
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

  // (3) Filter bar.
  var bar = document.getElementById('filters');
  if (!bar) return;
  bar.hidden = false;
  var inputs = bar.querySelectorAll('[data-filter]');
  var countEl = bar.querySelector('.filter-count');
  var noMatch = bar.parentNode.querySelector('#filter-empty');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.cards .card-inmate'));
  var months = Array.prototype.slice.call(document.querySelectorAll('details.month'));
  function currentFilters() {
    var f = {};
    inputs.forEach(function (i) { f[i.getAttribute('data-filter')] = (i.value || '').trim().toLowerCase(); });
    return f;
  }
  function apply() {
    var f = currentFilters();
    var active = !!(f.tier || f.chap || f.search);
    var shown = 0;
    cards.forEach(function (c) {
      var ok = true;
      if (f.tier && c.getAttribute('data-tier') !== f.tier) ok = false;
      if (ok && f.chap && c.getAttribute('data-chap') !== f.chap) ok = false;
      if (ok && f.search && (c.getAttribute('data-search') || '').indexOf(f.search) === -1) ok = false;
      c.classList.toggle('is-filtered-out', !ok);
      if (ok) shown++;
    });
    months.forEach(function (m) {
      var anyVisible = m.querySelector('.card-inmate:not(.is-filtered-out)');
      m.classList.toggle('is-empty', !anyVisible && active);
      if (active && anyVisible) m.open = true;
    });
    if (noMatch) noMatch.hidden = !(active && shown === 0);
    countEl.textContent = active ? (shown + ' of ' + cards.length + ' shown') : '';
  }
  inputs.forEach(function (i) {
    i.addEventListener('input', apply);
    i.addEventListener('change', apply);
  });
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
      bar.scrollIntoView({ block: 'start', behavior: 'smooth' });
    });
  }

  // (4) Search-results dropdown - lazy-loads search.json on first keystroke,
  //     shows a type-ahead list of matching people. Uses DOM APIs (not innerHTML)
  //     to satisfy CodeQL DOM-text-reinterpreted-as-HTML checks.
  var sbox = document.getElementById('search-box');
  var sresults = document.getElementById('search-results');
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
      if (!q || q.length < 2 || !idx) { sresults.hidden = true; sbox.setAttribute('aria-expanded', 'false'); return; }
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
      sbox.setAttribute('aria-expanded', 'true');
    }
    sbox.addEventListener('focus', loadIdx);
    sbox.addEventListener('input', function () { loadIdx(); render(); });
    sbox.addEventListener('keydown', function (e) { if (e.key === 'Escape') { sresults.hidden = true; sbox.setAttribute('aria-expanded', 'false'); } });
    document.addEventListener('click', function (e) {
      if (!sresults.contains(e.target) && e.target !== sbox) { sresults.hidden = true; sbox.setAttribute('aria-expanded', 'false'); }
    });
  }
})();
