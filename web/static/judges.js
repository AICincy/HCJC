/* Judges page filter: dedicated script for /judges/.
 *
 * Progressive enhancement: no-JS renders the full server-side list, all 30
 * judge cards visible. With JS, the search input filters on name, courtroom,
 * or room text and the court chips restrict the group. The count line always
 * carries the denominator ("Showing N of 30 judges"). Deep links like
 * /judges/#judge-jennifer-l-branch land on the card whether or not a filter
 * is active; typing or chip clicks never break the anchor id scheme.
 */
(function () {
  var input = document.getElementById('judge-filter');
  var countEl = document.getElementById('judge-filter-count');
  var emptyEl = document.getElementById('judge-filter-empty');
  var chips = Array.prototype.slice.call(
    document.querySelectorAll('#judge-court-chips button[data-court]')
  );
  var cards = Array.prototype.slice.call(document.querySelectorAll('.judge-card'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('.judges-section'));
  if (!input || !countEl || cards.length === 0) return;

  var total = cards.length;
  var courtFilter = 'all';

  function setPressed(active) {
    chips.forEach(function (b) {
      b.setAttribute('aria-pressed', b === active ? 'true' : 'false');
    });
  }

  chips.forEach(function (b) {
    b.addEventListener('click', function () {
      courtFilter = b.getAttribute('data-court');
      setPressed(b);
      applyFilter();
    });
  });
  input.addEventListener('input', applyFilter);

  function show(el, visible) {
    // Inline style, not the hidden attribute: .judge-card sets display:flex,
    // which would override the UA [hidden] rule under author styles.
    el.style.display = visible ? '' : 'none';
  }

  function applyFilter() {
    var q = (input.value || '').trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (card) {
      var okCourt = courtFilter === 'all' || card.getAttribute('data-court') === courtFilter;
      var okText = !q || (card.getAttribute('data-search') || '').indexOf(q) !== -1;
      var ok = okCourt && okText;
      show(card, ok);
      if (ok) shown++;
    });
    sections.forEach(function (sec) {
      var anyVisible = false;
      Array.prototype.slice.call(sec.querySelectorAll('.judge-card')).forEach(function (card) {
        if (card.style.display !== 'none') anyVisible = true;
      });
      show(sec, anyVisible);
    });
    countEl.textContent = 'Showing ' + shown + ' of ' + total + ' judges';
    if (emptyEl) show(emptyEl, shown === 0);
  }

  applyFilter();
})();
