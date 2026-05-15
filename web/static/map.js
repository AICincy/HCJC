// Homepage-only: when the map scrolls near the viewport, lazily inject Leaflet
// (vendored locally at /static/vendor/leaflet/) and plot dispatches.json on
// OpenStreetMap tiles. Points are grouped into a coarse grid so dense areas
// read as sized clusters, not an opaque blob.
// Vendoring locally means no CDN dependency - ad blockers, corp firewalls,
// and offline-cache browsers all load the map cleanly. If even the local
// asset fails (e.g., 404 because someone deleted the file), the box is
// replaced with a one-line note and the dispatch + shooting lists below
// still work as the visible fallback.
(function () {
  var el = document.getElementById('cfs-map');
  if (!el) return;
  var ROOT = document.documentElement.dataset.baseUrl || '';
  var SRC = el.getAttribute('data-src') || 'dispatches.json';
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c];});}
  function fail(msg){ el.classList.add('cfs-map-failed'); el.innerHTML = '<p class="muted" style="padding:1rem">' + (msg||'Map unavailable.') + ' The same calls are listed in the sections below this map &mdash; scroll down to see &ldquo;Recent CFS&rdquo; and &ldquo;Recent reported shootings&rdquo;.</p>'; }
  function withLeaflet(cb){
    if (window.L) return cb();
    var css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = ROOT + '/static/vendor/leaflet/leaflet.css';
    document.head.appendChild(css);
    var s = document.createElement('script');
    s.src = ROOT + '/static/vendor/leaflet/leaflet.js';
    s.onload = function(){ cb(); };
    s.onerror = function(){ fail('Map library could not load.'); };
    document.head.appendChild(s);
  }
  // ~0.0028deg cells ~= 250-310 m at this latitude.
  var CELL = 0.0028;
  function clusterize(pts){
    var cells = {};
    for (var i = 0; i < pts.length; i++){
      var p = pts[i];
      if (typeof p.la !== 'number' || typeof p.lo !== 'number') continue;
      var key = Math.round(p.la / CELL) + '|' + Math.round(p.lo / CELL);
      var c = cells[key] || (cells[key] = { la:0, lo:0, n:0, shoot:0, items:[] });
      c.la += p.la; c.lo += p.lo; c.n++;
      if (p.k === 'shooting') c.shoot++;
      if (c.items.length < 6) c.items.push(p);
    }
    var out = [];
    for (var k in cells){ var cc = cells[k]; out.push({ la: cc.la/cc.n, lo: cc.lo/cc.n, n: cc.n, shoot: cc.shoot, items: cc.items }); }
    return out;
  }
  function popupHtml(c){
    var head = c.n + ' call' + (c.n === 1 ? '' : 's');
    if (c.shoot) head += ' &middot; ' + c.shoot + ' shooting' + (c.shoot === 1 ? '' : 's');
    var html = '<strong>' + head + '</strong>';
    for (var i = 0; i < c.items.length; i++){
      var p = c.items[i], bits = [];
      if (p.d) bits.push(esc(p.d));
      if (p.a) bits.push(esc(p.a));
      if (p.t) bits.push('<span style="opacity:.6">' + esc(p.t) + '</span>');
      if (bits.length) html += '<br>' + bits.join(' &middot; ');
    }
    if (c.n > c.items.length) html += '<br><span style="opacity:.6">+ ' + (c.n - c.items.length) + ' more in this block</span>';
    return html;
  }
  function start(){
    fetch(SRC).then(function(r){ if(!r.ok) throw 0; return r.json(); }).then(function(d){
      var pts = (d && d.points) || [];
      if (!pts.length){ var sec = el.closest('.dispatch-map-section'); if (sec) sec.style.display='none'; else el.style.display='none'; return; }
      withLeaflet(function(){
        try {
          el.innerHTML = '';
          // Hamilton County, OH bounding box (approx). Locking the view here
          // keeps the map focused on the dispatch jurisdiction even if a
          // single noisy data point lands outside, and prevents users from
          // pan-drifting to other parts of the country.
          var HC_BOUNDS = L.latLngBounds([39.05, -84.82], [39.31, -84.27]);
          var map = L.map(el, {
            scrollWheelZoom: false,
            maxBounds: HC_BOUNDS,
            maxBoundsViscosity: 0.9,
            minZoom: 10
          });
          map.fitBounds(HC_BOUNDS, { padding: [8, 8] });
          // Esri World Imagery as default - free, no API key, refreshed
          // every 6-12 months for major US metros, ~30-60 cm/pixel in
          // Cincinnati. Attribution-only per Esri's terms of use. OSM
          // available as a cartographic alternate via the layer control.
          // Labels overlay (Esri Reference) adds street and place names
          // on top of satellite imagery without baking them into the tiles.
          var sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19,
            attribution: 'Imagery &copy; <a href="https://www.esri.com">Esri</a>, Maxar, Earthstar Geographics'
          });
          var labels = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19,
            attribution: ''
          });
          var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          });
          // Default: satellite + reference labels (group via layerGroup).
          var satWithLabels = L.layerGroup([sat, labels]);
          satWithLabels.addTo(map);
          L.control.layers({ 'Satellite': satWithLabels, 'Map': osm }, null, { position: 'topright', collapsed: false }).addTo(map);
          var bounds = [];
          clusterize(pts).forEach(function(c){
            var r = c.n === 1 ? 4 : Math.min(18, 5 + Math.round(Math.sqrt(c.n) * 2));
            var mk = L.circleMarker([c.la, c.lo], {
              radius: r,
              color: c.shoot ? '#ef6b6b' : '#d4915c',
              weight: 1, opacity: 0.9,
              fillOpacity: c.n > 1 ? 0.30 : 0.55
            }).addTo(map);
            mk.bindPopup(popupHtml(c), { maxWidth: 280 });
            bounds.push([c.la, c.lo]);
          });
          // Re-fit to data bounds only if they sit inside the county; otherwise
          // keep the county-wide view we set above so a single outlier point
          // doesn't yank the map elsewhere.
          if (bounds.length) {
            var dataBounds = L.latLngBounds(bounds);
            if (HC_BOUNDS.contains(dataBounds)) {
              map.fitBounds(dataBounds, { padding:[24,24], maxZoom:13 });
            }
          }
        } catch (e) { fail('Map failed to render.'); }
      });
    }).catch(function(){ fail('Dispatch data unavailable.'); });
  }
  if ('IntersectionObserver' in window){
    var io = new IntersectionObserver(function(entries){
      for (var i = 0; i < entries.length; i++){ if (entries[i].isIntersecting){ io.disconnect(); start(); return; } }
    }, { rootMargin: '600px 0px' });
    io.observe(el);
  } else { start(); }
})();
