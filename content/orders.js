"use strict";

(() => {
  if (!HakariTracking.isOrderPage(location.href)) return;
  const selector = '#packagesTable [id^="package-number-details-"] .package-number';
  const observer = new MutationObserver(schedule);
  let pending = false;

  function update() {
    pending = false;
    observer.disconnect();
    try {
      const carrier = document.querySelector('#tr_firma-kurierska .delivery-name')?.textContent || "";
      for (const field of document.querySelectorAll(selector)) {
        const ownLink = field.querySelector('a[data-hakari-tracking]');
        // Preserve links supplied by the panel or another extension.
        if (!ownLink && field.querySelector('a')) continue;
        const result = HakariTracking.resolve(carrier, field.textContent);
        if (!result) {
          if (ownLink) ownLink.replaceWith(document.createTextNode(ownLink.textContent));
          continue;
        }
        const link = ownLink || document.createElement('a');
        if (!ownLink) {
          link.textContent = field.textContent;
          link.dataset.hakariTracking = "true";
          field.replaceChildren(link);
        }
        link.href = result.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.referrerPolicy = "no-referrer";
        link.title = `Śledź przesyłkę — ${result.carrier} (nowa karta)`;
        link.setAttribute('aria-label', `Śledź przesyłkę ${result.number} — ${result.carrier}, nowa karta`);
      }
    } finally {
      observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    }
  }

  function schedule() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(update);
  }

  update();
})();
