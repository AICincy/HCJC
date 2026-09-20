/* Bond schedule filter: dedicated script for /bond-schedule/.
 * Progressive enhancement: no-JS renders the full table.
 * Case-insensitive substring over offense + ORC.
 * ORC normalization: 4511.19 / 4511-19 / 451119 -> 451119 digits; strip * suffixes.
 */
(function () {
  var input = document.getElementById('bond-filter');
  var count = document.getElementById('bond-filter-count');
  if (!input || !count) return;

  function normalizeORC(s) {
    return (s || '').toLowerCase().replace(/[^0-9]/g, '');
  }
  function normalizeText(s) {
    return (s || '').toLowerCase();
  }

  var rows = Array.prototype.slice.call(document.querySelectorAll('table.schedule tbody tr[data-offense]'));
  var noBondRows = Array.prototype.slice.call(document.querySelectorAll('.no-bond-row[data-offense]'));
  var totalRows = rows.length;
  var totalNoBond = noBondRows.length;

  function applyFilter() {
    var q = normalizeText(input.value.trim());
    var qDigits = normalizeORC(q);
    var shownRows = 0;

    rows.forEach(function (tr) {
      var offense = normalizeText(tr.getAttribute('data-offense'));
      var orc = tr.getAttribute('data-orc') || '';
      var orcNorm = normalizeORC(orc);
      var match = false;
      if (!q) {
        match = true;
      } else {
        if (offense.indexOf(q) !== -1) match = true;
        if (orc.toLowerCase().indexOf(q) !== -1) match = true;
        if (qDigits && orcNorm.indexOf(qDigits) !== -1) match = true;
      }
      if (match) {
        tr.removeAttribute('hidden');
        shownRows++;
      } else {
        tr.setAttribute('hidden', '');
      }
    });

    var shownNoBond = 0;
    noBondRows.forEach(function (div) {
      var offense = normalizeText(div.getAttribute('data-offense'));
      var orc = div.getAttribute('data-orc') || '';
      var orcNorm = normalizeORC(orc);
      var match = false;
      if (!q) {
        match = true;
      } else {
        if (offense.indexOf(q) !== -1) match = true;
        if (orc.toLowerCase().indexOf(q) !== -1) match = true;
        if (qDigits && orcNorm.indexOf(qDigits) !== -1) match = true;
      }
      if (match) {
        div.removeAttribute('hidden');
        shownNoBond++;
      } else {
        div.setAttribute('hidden', '');
      }
    });

    // Focus recovery: if focused element was hidden, move focus to input
    var active = document.activeElement;
    if (active && active.hasAttribute && active.hasAttribute('hidden')) {
      input.focus();
    }

    if (!q) {
      count.textContent = totalRows + ' of ' + totalRows + ' schedule rows shown. ' + totalNoBond + ' no-standard-bond offenses listed below.';
    } else if (shownRows === 0 && shownNoBond === 0) {
      count.textContent = 'No matches for "' + input.value.trim() + '". Try an ORC code (e.g. 4511.19), or browse the full table below.';
    } else {
      count.textContent = shownRows + ' of ' + totalRows + ' schedule rows shown. ' + shownNoBond + ' of ' + totalNoBond + ' no-standard-bond offenses shown.';
    }
  }

  input.addEventListener('input', applyFilter);
})();
