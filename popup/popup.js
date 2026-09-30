"use strict";

const form = document.querySelector("#note-form");
const note = document.querySelector("#note");
const save = document.querySelector("#save");
const status = document.querySelector("#status");

async function loadNote() {
  try {
    const stored = await chrome.storage.local.get("note");
    note.value = typeof stored.note === "string" ? stored.note : "";
    note.disabled = false;
    save.disabled = false;
    status.textContent = "Gotowe.";
  } catch (error) {
    status.textContent = "Nie udało się wczytać notatki. Otwórz panel ponownie.";
    console.error("Hakari: odczyt notatki", error);
  }
}

note.addEventListener("input", () => {
  status.textContent = "Masz niezapisane zmiany.";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  save.disabled = true;
  note.disabled = true;
  status.textContent = "Zapisywanie…";
  try {
    await chrome.storage.local.set({ note: note.value });
    status.textContent = "Notatka zapisana.";
  } catch (error) {
    status.textContent = "Nie udało się zapisać. Spróbuj ponownie.";
    console.error("Hakari: zapis notatki", error);
  } finally {
    save.disabled = false;
    note.disabled = false;
  }
});

loadNote();
