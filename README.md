# Hakari — Google Chrome

Rozszerzenie Manifest V3 zamieniające numery paczek w panelu IdoSell kartony24h.com w linki do śledzenia. Wersja 0.3.0 jest przygotowana dla Chrome 95 lub nowszego. Nie wymaga bibliotek, kompilacji ani podpisu cyfrowego do lokalnych testów.

## Instalacja do testów — bez podpisu

1. Otwórz `chrome://extensions` w Google Chrome.
2. Włącz **Tryb dewelopera** w prawym górnym rogu.
3. Kliknij **Załaduj rozpakowane**.
4. Wybierz folder `C:\Users\Maks\Documents\GitHub\Hakari` (cały folder, nie plik manifest.json).
5. Otwórz lub odśwież zamówienie w kartony24h.com. Kliknij numer w sekcji „Przesyłka”.

Jeżeli korzystasz z ZIP, najpierw go rozpakuj i wybierz folder zawierający `manifest.json`. Nie używaj wcześniejszego XPI dla Firefoksa. Zachowaj folder na dysku: Chrome korzysta z tych plików. Po zmianach kliknij ikonę przeładowania na karcie Hakari w `chrome://extensions`, a następnie odśwież zamówienie.

Ten tryb służy testom lokalnym. Publikacja w Chrome Web Store jest osobnym procesem i nie została wykonana.

## Działanie

Rozszerzenie działa tylko na `https://kartony24h.com/panel/orderd.php?idt=…` oraz `/panel/app/orderd.php?idt=…`, także wewnątrz ramki starego panelu. Odczytuje przewoźnika z pola „Kurier”, nie z notatek. Każdy numer paczki otwiera śledzenie w nowej karcie. Obsługuje wiele paczek i aktualizacje danych bez przeładowania.

Przewoźnicy: GLS, InPost, DPD, DHL, UPS, Pocztex / Poczta Polska, ORLEN Paczka i FedEx. Rozpoznawane są warianty typu „Allegro Kurier DPD”, „Allegro Paczkomaty InPost” i „DHL eCommerce”. Nieznane i niejednoznaczne nazwy pozostają tekstem. Allegro One / Delivery oraz numery AD nie są jeszcze obsługiwane. [Informacja ORLEN o Allegro Delivery](https://www.orlenpaczka.pl/sledz-paczke/).

Numery nie są zapisywane ani wysyłane w tle. Dopiero kliknięcie przekazuje numer stronie przewoźnika, bez adresu panelu w nagłówku Referer. Przykładowa notatka w panelu dodatku jest zapisywana lokalnie przez `chrome.storage.local`; usunięcie dodatku lub profilu może ją usunąć.

## Pliki

- `manifest.json` — konfiguracja Chrome i ograniczenie stron.
- `content/tracking.js` — przewoźnicy i adresy śledzenia.
- `content/orders.js`, `content/orders.css` — linki w panelu i ich wygląd.
- `popup/` — panel dodatku i lokalna notatka.
- `icons/hakari-*.png` — ikony dla Chrome; SVG pozostaje źródłem i grafiką panelu.
- `tests/` — testy rozpoznawania, panelu oraz przykładowego układu IdoSell.

## Weryfikacja

Uruchom `node --test tests/*.test.cjs`. Testy sprawdzają zakres adresów, nazwy przewoźników, parametry numerów oraz odczyt, zapis i błędy notatki z interfejsem Chrome. Walidacja manifestu obejmuje istnienie plików oraz format i wymiary ikon PNG.

`tests/dom.html` testuje na sztucznych danych: tworzenie linku, zachowanie przycisków, zmianę kuriera i numeru, drugą paczkę i usuwanie nieaktualnych linków. Test przeszedł w przeglądarce przed migracją; kod śledzenia nie zmienił się podczas migracji.

Automatyczne wyszukiwanie GLS potwierdzono na testowym numerze. Pozostałe trasy wymagają sprawdzenia na rzeczywistych przesyłkach. Testy nie zastępują sprawdzenia załadowanego rozszerzenia na zalogowanym panelu.

## Dokumentacja Chrome

- [Ładowanie rozpakowanego rozszerzenia](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world)
- [Ikony — bez obsługi SVG w manifeście](https://developer.chrome.com/docs/extensions/develop/ui/configure-icons)
- [chrome.storage](https://developer.chrome.com/docs/extensions/reference/api/storage)
