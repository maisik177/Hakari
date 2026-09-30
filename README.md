# Hakari

Szkielet rozszerzenia Mozilla Firefox (Manifest V3), napisany w zwykłym HTML, CSS i JavaScript. Nie wymaga instalacji bibliotek ani kompilowania.

## Uruchomienie

1. Otwórz Firefox 140 lub nowszy.
2. Wpisz `about:debugging#/runtime/this-firefox` w pasku adresu.
3. Kliknij „Wczytaj tymczasowy dodatek…” i wybierz `manifest.json` z tego folderu.
4. Otwórz Hakari z menu rozszerzeń (ikona puzzla). Możesz przypiąć je do paska narzędzi.
5. Wpisz notatkę, zapisz ją i otwórz panel ponownie, aby sprawdzić zapis.

Instalacja tymczasowa kończy się po ponownym uruchomieniu Firefoksa. To tryb pracy nad dodatkiem, nie instalacja produkcyjna. Nie traktuj notatki jako kopii zapasowej; usunięcie dodatku lub profilu może usunąć jej dane.

## Pliki

- `manifest.json` — nazwa, wersja, uprawnienia i konfiguracja Firefoksa.
- `popup/popup.html` — zawartość panelu.
- `popup/popup.css` — wygląd panelu.
- `popup/popup.js` — zapis i odczyt przykładowej notatki.
- `icons/hakari.svg` — ikona rozszerzenia.

Po zmianach kliknij „Wczytaj ponownie” przy Hakari w `about:debugging` i ponownie otwórz panel. Konsolę rozszerzenia otwiera przycisk „Zbadaj”.

## Założenia

Notatka to przykładowa funkcja do zastąpienia docelową funkcjonalnością Hakari. Rozszerzenie używa wyłącznie uprawnienia `storage`, przechowuje dane w `browser.storage.local` i nie wysyła ich do sieci. Nie odczytuje otwartych stron. Skrypty stron i skrypt tła można dodać, kiedy będą potrzebne.

Identyfikator `hakari@maisik177.extensions` jest identyfikatorem dodatku, a nie adresem kontaktowym. Ustal go przed pierwszą publikacją i później zachowaj. Deklaracja `data_collection_permissions` odpowiada obecnej wersji bez transmisji danych; aktualizuj ją, jeśli funkcje dodatku się zmienią.

## Sprawdzenie przed publikacją

- Zapisz tekst, zamknij panel i ponownie go otwórz.
- Zapisz pustą notatkę i upewnij się, że poprzedni tekst znika.
- Sprawdź obsługę klawiaturą (Tab, Shift+Tab, Enter na przycisku).
- Sprawdź brak błędów w konsoli rozszerzenia.

Publikacja wymaga osobnego przygotowania i podpisania dodatku przez Mozillę. Ten szkielet nie został opublikowany.

## Dokumentacja

- [Pierwsze rozszerzenie — MDN](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Your_first_WebExtension)
- [Konfiguracja Firefoksa — MDN](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/browser_specific_settings)
- [Lokalny magazyn danych — MDN](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/storage/local)

## Śledzenie przesyłek (0.2.0)

Rozszerzenie odczytuje tylko szczegóły zamówień `https://kartony24h.com/panel/orderd.php?idt=…` oraz wariant `/panel/app/orderd.php?idt=…`. Działa także wewnątrz ramki starego panelu (`all_frames`). Numer w `.package-number` staje się linkiem do śledzenia w nowej karcie. Przewoźnik pochodzi wyłącznie z pola „Kurier” (`#tr_firma-kurierska .delivery-name`), nigdy z notatki do zamówienia. Obsługiwane są nowe paczki i zmiany danych bez przeładowania strony.

Przewoźnicy: GLS, InPost, DPD, DHL, UPS, Pocztex / Poczta Polska, ORLEN Paczka, FedEx. Rozpoznawane są warianty takie jak „Allegro Kurier DPD”, „Allegro Paczkomaty InPost” i „DHL eCommerce”. Nieznane i niejednoznaczne nazwy pozostają zwykłym tekstem. Allegro One / Delivery oraz numery AD wymagają osobnej integracji i obecnie również pozostają tekstem. ORLEN informuje, że przesyłki Allegro Delivery są śledzone przez Allegro: https://www.orlenpaczka.pl/sledz-paczke/.

Nie ma zapytań sieciowych w tle ani zapisu numerów. Dopiero kliknięcie linku przekazuje numer stronie przewoźnika; adres panelu nie jest przekazywany jako Referer. Funkcja notatki pozostaje lokalna. Dotychczasowa informacja, że dodatek nie odczytuje stron, dotyczyła szkieletu 0.1.0.

### Uruchomienie nowej funkcji

W `about:debugging#/runtime/this-firefox` wczytaj ponownie Hakari (albo wybierz ten manifest przez „Wczytaj tymczasowy dodatek…”), zaakceptuj dostęp do kartony24h.com, jeżeli Firefox o niego poprosi, i odśwież stronę zamówienia. Kliknij numer w sekcji „Przesyłka”. Instalacja tymczasowa znika po restarcie Firefoksa.

### Weryfikacja

- `node --test tests/tracking.test.cjs` — ograniczenie adresów, warianty nazw, zachowanie zer wiodących, nieznane nazwy i błędne numery.
- `tests/dom.html` — lokalny test na sztucznych danych w strukturze odczytanej z panelu: tworzenie linku, zachowanie przycisków, zmiana kuriera/numeru, dodanie drugiej paczki i usuwanie nieaktualnych linków.
- Potwierdzono w przeglądarce, że link GLS automatycznie wyszukuje testowy numer. Pozostałe trasy wymagają sprawdzenia na rzeczywistych przesyłkach każdego przewoźnika. Test lokalny nie zastępuje testu załadowanego rozszerzenia w Firefox.

Pliki funkcji: `content/tracking.js`, `content/orders.js`, `content/orders.css`. Brak bibliotek i etapu kompilacji.
