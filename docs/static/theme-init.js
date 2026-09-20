/* Theme pre-paint init: runs synchronously in <head> so first paint uses the
   right tokens (no light-flash). Default is dark; a saved choice in
   localStorage wins. No-JS falls back to the light theme. External file
   (not inline) to satisfy the site's script-src 'self' CSP. */
(function () {
  var t = 'dark';
  try {
    var s = localStorage.getItem('jcstream-theme');
    if (s === 'light' || s === 'dark') t = s;
  } catch (e) { /* storage unavailable: stay on the dark default */ }
  document.documentElement.setAttribute('data-theme', t);
  /* Keep the browser chrome in sync pre-paint too: main.js only re-syncs
     this once its deferred bundle runs, which is too late when the saved
     theme is light. Values match main.js syncThemeMeta exactly. */
  var m = document.querySelector('meta[name="theme-color"]');
  if (m) m.setAttribute('content', t === 'light' ? '#F5F0EB' : '#141619');
})();
