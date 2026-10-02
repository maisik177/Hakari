/* Autor: Maksymilian Dyla, firma Cart-pack */
"use strict";

// Shared by the content script and the dependency-free Node tests.
const HakariTracking = (() => {
  const carriers = [
    ["GLS", /\bgls\b/, "https://gls-group.com/PL/pl/sledzenie-paczek/", "match"],
    ["InPost", /\binpost\b/, "https://inpost.pl/sledzenie-przesylek", "number"],
    ["DPD", /\bdpd\b/, "https://tracktrace.dpd.com.pl/parcelDetails", "p1"],
    ["DHL", /\bdhl\b/, "https://www.dhl.com/pl-pl/home/sledzenie-przesylek.html", "tracking-id"],
    ["UPS", /\bups\b/, "https://www.ups.com/track?loc=pl_PL", "tracknum"],
    ["Pocztex / Poczta Polska", /\bpocztex\b|\bpoczta\s+polska\b/, "https://emonitoring.poczta-polska.pl/", "numer"],
    ["ORLEN Paczka", /\borlen\b|\bpaczka\s+w\s+ruchu\b/, "https://www.orlenpaczka.pl/sledz-paczke/", "numer"],
    ["FedEx", /\bfedex\b/, "https://www.fedex.com/fedextrack/?locale=pl_PL", "trknbr"]
  ];

  function isOrderPage(href) {
    const url = new URL(href);
    return url.origin === "https://kartony24h.com" &&
      ["/panel/orderd.php", "/panel/app/orderd.php"].includes(url.pathname) &&
      Boolean(url.searchParams.get("idt"));
  }

  function resolve(name, rawNumber) {
    const number = rawNumber.trim().replace(/\s+/g, "");
    if (!/^[a-z0-9-]{6,40}$/i.test(number) || !/\d/.test(number)) return null;
    const normalized = name.normalize("NFKC").toLowerCase();
    // Allegro Delivery has its own tracking IDs, not the partner's IDs.
    // Do not send these to a partner's search until its route is verified.
    if (/^AD/i.test(number) || /\ballegro\s+(?:one|delivery)\b/.test(normalized)) return null;
    const matches = carriers.filter(([, pattern]) => pattern.test(normalized));
    if (matches.length !== 1) return null;
    const [carrier, , base, parameter] = matches[0];
    const url = new URL(base);
    url.searchParams.set(parameter, number);
    return { carrier, number, url: url.href };
  }

  return { isOrderPage, resolve };
})();

if (typeof module !== "undefined") module.exports = HakariTracking;
