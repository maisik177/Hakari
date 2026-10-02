"use strict";
async function sendOrders(message, sender) {
  const url = new URL(sender.url || "about:blank");
  if (sender.id !== chrome.runtime.id || url.origin !== "https://kartony24h.com" ||
      !url.pathname.startsWith("/panel/")) {
    throw new Error("Niedozwolone źródło zamówień.");
  }
  if (!Array.isArray(message.ids) || !message.ids.length || message.ids.length > 5000 ||
      message.ids.some(id => typeof id !== "string" || !/^[1-9][0-9]{0,19}$/.test(id)) ||
      typeof message.requestId !== "string" || !/^[0-9a-f-]{36}$/.test(message.requestId)) {
    throw new Error("Nieprawidłowe ID zamówień.");
  }
  const {bridgeToken} = await chrome.storage.local.get("bridgeToken");
  if (!bridgeToken) throw new Error("Wklej klucz połączenia z Pythonem w panelu Hakari.");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch("http://127.0.0.1:8765/orders", {
      method: "POST", signal: controller.signal, credentials: "omit", redirect: "error",
      headers: {"Content-Type": "application/json", "Authorization": `Bearer ${bridgeToken}`},
      body: JSON.stringify({request_id: message.requestId, shop: "kartony24h.com", order_ids: [...new Set(message.ids)]})
    });
    if (response.status === 401) throw new Error("Nieprawidłowy klucz połączenia. Sprawdź ustawienia Hakari.");
    if (!response.ok) throw new Error(`Odbiornik Python zgłosił błąd (${response.status}).`);
    const data = await response.json();
    if (data.request_id !== message.requestId || data.accepted !== new Set(message.ids).size) {
      throw new Error("Odbiornik nie potwierdził wszystkich ID.");
    }
    return {ok: true, accepted: data.accepted};
  } catch (error) {
    if (error.name === "AbortError" || error instanceof TypeError) {
      throw new Error("Brak połączenia z Pythonem. Uruchom odbiornik i ponów wysyłanie — ta sama paczka nie zostanie zapisana dwukrotnie.");
    }
    throw error;
  } finally { clearTimeout(timeout); }
}
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (message?.type !== "hakari.sendOrders") return;
  sendOrders(message, sender).then(reply, error => reply({ok: false, error: error.message}));
  return true;
});
