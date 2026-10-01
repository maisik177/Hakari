"use strict";
const HakariSelection = (() => {
  function read(doc) {
    const boxes = [...doc.querySelectorAll('#dynamicdata input[type="checkbox"][name="idt[]"]:checked')];
    const ids = boxes.map(box => box.value);
    if (ids.some(id => !/^[1-9][0-9]{0,19}$/.test(id))) {
      throw new Error("Nie udało się odczytać ID. Odśwież listę zamówień.");
    }
    return [...new Set(ids)];
  }
  return { read };
})();
if (typeof module !== "undefined") module.exports = HakariSelection;
