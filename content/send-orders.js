"use strict";
(() => {
  if (location.origin !== "https://kartony24h.com" || !location.pathname.startsWith("/panel/")) return;
  let busy = false;
  let previousKey = "";
  let requestId = "";
  const bar = document.createElement("section");
  bar.id = "hakari-send-orders";
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Hakari — przekaż zaznaczone do Python";
  const status = document.createElement("span");
  status.setAttribute("role", "status");
  status.textContent = "Wysyłane są tylko ID zaznaczone na bieżącej stronie listy.";
  bar.append(button, status);
  function mount() {
    const list = document.querySelector("#dynamicdata");
    // The panel reuses its order table across search, status and operator views.
    // Do not show the control on unrelated panel tables or in the outer app frame.
    const isOrderList = list && (list.querySelector('input[name="idt[]"]') ||
      list.querySelector('[id$="-th-id"]')) && document.querySelector("#counterOrders");
    if (!isOrderList) {
      if (bar.isConnected) bar.remove();
      return;
    }
    if (!bar.isConnected || bar.nextElementSibling !== list) list.before(bar);
  }
  new MutationObserver(mount).observe(document.body, {childList: true, subtree: true});
  mount();
  button.addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    button.disabled = true;
    try {
      const ids = HakariSelection.read(document);
      if (!ids.length) throw new Error("Najpierw zaznacz zamówienia na liście.");
      const key = [...ids].sort().join(",");
      // Reuse the receipt key when retrying a potentially delivered request.
      if (key !== previousKey) {
        requestId = crypto.randomUUID();
        previousKey = key;
      }
      status.textContent = `Przekazywanie ${ids.length} zamówień…`;
      const result = await chrome.runtime.sendMessage({type: "hakari.sendOrders", ids, requestId});
      if (!result?.ok) throw new Error(result?.error || "Brak potwierdzenia odbioru.");
      status.textContent = `Zapisano ${result.accepted} ID w kolejce Python. Dalsze przetwarzanie jeszcze nie zostało wykonane.`;
    } catch (error) {
      status.textContent = error.message || "Nie udało się wysłać ID. Spróbuj ponownie.";
    } finally {
      busy = false;
      button.disabled = false;
    }
  });
})();
