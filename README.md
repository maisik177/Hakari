<!-- Autor: Maksymilian Dyla, firma Cart-pack -->
# Hakari — Google Chrome

Rozszerzenie Manifest V3 zamieniające numery paczek w panelu IdoSell kartony24h.com w linki do śledzenia oraz przekazujące zaznaczone ID zamówień do lokalnego odbiornika Python. Wersja 0.4.1 jest przygotowana dla Chrome 95 lub nowszego. Nie wymaga bibliotek, kompilacji ani podpisu cyfrowego do lokalnych testów.

## Przekazywanie ID do Python

1. Uruchom dwuklikiem `python/start-receiver.cmd`. Pozostaw jego okno otwarte. Wymagany jest Python 3.10+; skrypt potrafi też użyć Pythona dołączonego do Codex na tym komputerze.
2. Skopiuj klucz wyświetlony po `Connection key` do pola „Klucz połączenia z Pythonem” w panelu Hakari i zapisz.
3. Po aktualizacji plików przeładuj Hakari w `chrome://extensions` i odśwież listę zamówień. Jeśli Chrome wymaga potwierdzenia nowego dostępu lokalnego, zaakceptuj je, aby włączyć wysyłkę.
4. Na liście zamówień zaznacz wybrane pozycje i kliknij „Hakari — przekaż zaznaczone do Python” nad tabelą.
5. Komunikat „Zapisano … ID” potwierdza zapis w kolejce, a nie wykonanie dalszych operacji.

Listy zamówień są wykrywane po strukturze tabeli w panelu, także w ramce starego panelu. Obejmuje to wyszukiwanie oraz `orders-list.php` z filtrami statusu (np. Nieobsłużone, Pakowane), operatora i stronicowaniem. Przycisk jest przywracany po wymianie tabeli i ukrywany na stronach bez listy zamówień. Wysyłane są tylko zaznaczenia z bieżącej strony tabeli. Wtyczka nie zbiera zaznaczeń między stronami. Pole „zaznacz wszystko” samo nie jest ID zamówienia.

Odbiornik nasłuchuje wyłącznie na `127.0.0.1:8765`. Wtyczka wysyła ID jako tekst, nazwę sklepu i identyfikator paczki, bez danych klientów. Wymagany jest klucz lokalnego odbiornika, zapisywany w `python/data/connection-key.txt` i lokalnych ustawieniach wtyczki. Nie udostępniaj klucza. Folder danych jest pomijany przez Git.

### Podłączenie dalszego programu

`python/receiver.py` jest samodzielnym odbiornikiem, bez zewnętrznych bibliotek. Zapisuje paczki w SQLite: `python/data/inbox.sqlite3`, tabela `batches`, kolumny `request_id`, `shop`, `order_ids` (tablica JSON), `status` (początkowo `pending`), `received_at`. Docelowy program może odczytywać oczekujące paczki i oznaczać je po wykonaniu. Odbiornik nie zmienia statusów zamówień w IdoSell.

Protokół: `POST /orders`, nagłówek `Authorization: Bearer <klucz>`, JSON:

```json
{"request_id":"aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee","shop":"kartony24h.com","order_ids":["123","456"]}
```

Odpowiedź po trwałym zapisie: `{"request_id":"…","accepted":2}`. Ponowienie tego samego `request_id` nie tworzy drugiej paczki. Przycisk zachowuje ten identyfikator dla tej samej listy ID do przeładowania strony lub wysłania innego zestawu. Odświeżenie strony i nowa wysyłka tworzą nowe zlecenie; docelowe operacje wymagają własnej ochrony przed ponownym wykonaniem.

Testy odbiornika: `python -m unittest discover -s tests -p test_receiver.py -v`. Sprawdzają rzeczywiste lokalne HTTP, zapis SQLite, ponowienia, autoryzację i błędne dane. Testy JavaScript obejmują także wysyłkę, potwierdzenia i wybór ID. Strukturę selektorów zweryfikowano na otwartym panelu IdoSell (100 wierszy); wykrywanie zweryfikowano też na rzeczywistej liście Nieobsłużone. Testy obejmują dynamiczne doładowanie i wymianę tabeli oraz różne adresy list. Pełny test zainstalowanej aktualizacji Chrome wymaga przeładowania dodatku i konfiguracji klucza.

## Instalacja do testów — bez podpisu

1. Otwórz `chrome://extensions` w Google Chrome.
2. Włącz **Tryb dewelopera** w prawym górnym rogu.
3. Kliknij **Załaduj rozpakowane**.
4. Wybierz folder `C:\Users\Maks\Documents\GitHub\Hakari` (cały folder, nie plik manifest.json).
5. Otwórz lub odśwież zamówienie w kartony24h.com. Kliknij numer w sekcji „Przesyłka”.

Jeżeli korzystasz z ZIP, najpierw go rozpakuj i wybierz folder zawierający `manifest.json`. Nie używaj wcześniejszego XPI dla Firefoksa. Zachowaj folder na dysku: Chrome korzysta z tych plików. Po zmianach kliknij ikonę przeładowania na karcie Hakari w `chrome://extensions`, a następnie odśwież zamówienie.

Ten tryb służy testom lokalnym. Publikacja w Chrome Web Store jest osobnym procesem i nie została wykonana.

## Działanie

Śledzenie przesyłek działa na `https://kartony24h.com/panel/orderd.php?idt=…` oraz `/panel/app/orderd.php?idt=…`, także wewnątrz ramki starego panelu. Odczytuje przewoźnika z pola „Kurier”, nie z notatek. Każdy numer paczki otwiera śledzenie w nowej karcie. Obsługuje wiele paczek i aktualizacje danych bez przeładowania.

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

