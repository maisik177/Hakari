"use strict";
const bridgeForm = document.querySelector("#bridge-form");
const bridgeInput = document.querySelector("#bridge-token");
const bridgeStatus = document.querySelector("#bridge-status");
chrome.storage.local.get("bridgeToken").then(({bridgeToken}) => {
  if (bridgeToken) bridgeStatus.textContent = "Klucz jest zapisany. Połączenie: ten komputer, port 8765.";
}).catch(() => { bridgeStatus.textContent = "Nie udało się odczytać ustawień."; });
bridgeForm.addEventListener("submit", async event => {
  event.preventDefault();
  const token = bridgeInput.value.trim();
  if (!/^[a-zA-Z0-9_-]{32,128}$/.test(token)) {
    bridgeStatus.textContent = "Wklej cały klucz wyświetlony przez odbiornik Python.";
    return;
  }
  try {
    await chrome.storage.local.set({bridgeToken: token});
    bridgeInput.value = "";
    bridgeStatus.textContent = "Klucz zapisany. Możesz przekazywać zaznaczone zamówienia.";
  } catch { bridgeStatus.textContent = "Nie udało się zapisać klucza. Spróbuj ponownie."; }
});
