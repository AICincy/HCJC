/* Judge-card deep-link auto-open.
 * When a fragment targets an element inside a closed <details>,
 * open that card and any closed ancestors, then move focus to the
 * opened card's summary. Applies on initial load and hashchange.
 * Respects prefers-reduced-motion.
 */
(function () {
  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function openDeepLink() {
    var hash = window.location.hash;
    if (!hash || hash.length < 2) return;
    var id = decodeURIComponent(hash.slice(1));
    var target = document.getElementById(id);
    if (!target) return;

    // Find the closest judge-card or details ancestor
    var detailsToOpen = [];
    var el = target;
    // If target itself is a details, include it
    if (el.tagName && el.tagName.toLowerCase() === 'details') {
      detailsToOpen.push(el);
    }
    // Walk up through ancestors
    var parent = el.parentElement;
    while (parent) {
      if (parent.tagName && parent.tagName.toLowerCase() === 'details' && !parent.open) {
        detailsToOpen.push(parent);
      }
      parent = parent.parentElement;
    }

    if (detailsToOpen.length === 0) return;

    detailsToOpen.forEach(function (d) {
      d.open = true;
    });

    // Move focus to the opened card's summary (the judge-card if present, else first opened)
    var focusDetails = null;
    // Prefer the judge-card
    for (var i = 0; i < detailsToOpen.length; i++) {
      if (detailsToOpen[i].classList && detailsToOpen[i].classList.contains('judge-card')) {
        focusDetails = detailsToOpen[i];
        break;
      }
    }
    if (!focusDetails) focusDetails = detailsToOpen[0];

    var summary = focusDetails.querySelector('summary');
    if (summary) {
      // Make summary focusable if not already
      if (!summary.hasAttribute('tabindex')) {
        summary.setAttribute('tabindex', '-1');
      }
      // Use preventScroll then scroll manually respecting reduced motion
      try {
        summary.focus({ preventScroll: true });
      } catch (e) {
        summary.focus();
      }
      if (!prefersReducedMotion()) {
        summary.scrollIntoView({ block: 'start', behavior: 'smooth' });
      } else {
        summary.scrollIntoView({ block: 'start' });
      }
    }
  }

  document.addEventListener('DOMContentLoaded', openDeepLink);
  window.addEventListener('hashchange', openDeepLink);
  // Also run immediately in case DOM is already ready
  if (document.readyState === 'interactive' || document.readyState === 'complete') {
    openDeepLink();
  }
})();
