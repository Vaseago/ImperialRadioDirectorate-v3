/* Embed mode - mark every button so ICD can tighten the spacing between them.
 *
 * Inside the Imperial Command Directorate (ICD) the buttons of a page are pulled almost together
 * (ICD's docs/EMBED_CONTRACT.md, section 4: the `button` sticker). This script marks every
 * <button> (and role="button" / a.btn link) with data-icd-panel="button", the ones already on
 * the page and the ones added later (a MutationObserver) - not stamped by hand at each place.
 *
 * Only does anything in embed mode (the boot script in index.html sets data-embed="1"). A normal
 * visit changes nothing: no attribute is added and no observer is installed. The attribute is
 * inert; ICD's injected stylesheet uses it for spacing only. Never touches the audio element. */
(function () {
  if (document.documentElement.dataset.embed !== "1") return;

  var SELECTOR = 'button, [role="button"], a.btn';

  function mark(el) {
    if (!el.dataset.icdPanel) el.dataset.icdPanel = "button";
  }

  function stamp(node) {
    if (node.nodeType !== 1) return;
    if (node.matches(SELECTOR)) mark(node);
    node.querySelectorAll(SELECTOR).forEach(mark);
  }

  stamp(document.body);
  new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      mutation.addedNodes.forEach(stamp);
    });
  }).observe(document.body, { childList: true, subtree: true });
})();
