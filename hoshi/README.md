<!-- Autor: Maksymilian Dyla, firma Cart-pack -->
# Hoshi 0.1

Podprojekt Hakari: pobieranie danych zamówień z API IdoSell i tworzenie zwartych kart do drukowania na A4. Kilka zamówień na stronie; zdjęcia osadzone w HTML. Program tylko odczytuje API, nie zmienia zamówień, płatności ani dokumentów.

## Uruchomienie

1. Uruchom `start-hoshi.cmd` w tym folderze. Wymagany Windows i Python 3.10+ z Tkinter. Skrypt korzysta również z Pythona dołączonego do Codex na tym komputerze.
2. Przy pierwszym uruchomieniu wybierz **Importuj / zmień klucz API z pliku…** i wskaż plik tekstowy zawierający sam klucz.
3. Wpisz numery zamówień i wybierz **Generuj i otwórz wydruk**.
4. W przeglądarce: Ctrl+P, A4, skala 100%, wyłącz nagłówki i stopki. Można wydrukować lub wybrać „Zapisz jako PDF”.

## Współpraca z Hakari (opcjonalna)

Samodzielne generowanie po numerach nie wymaga rozszerzenia ani nasłuchiwacza. Obsługa kolejki wymaga osobno zainstalowanej wersji Hakari z odbiornikiem Python; nie jest ona częścią tego folderu ani obecnej wersji głównej rozszerzenia.

Uruchom także `../python/start-receiver.cmd` i skonfiguruj jego osobny klucz połączenia w rozszerzeniu Hakari. Zaznacz zamówienia w panelu i przekaż je przyciskiem Hakari. W Hoshi wybierz **Pobierz kolejkę Hakari** albo włącz odbieranie co 5 sekund.

Nasłuchiwacz przekazuje tylko numery zamówień; szczegóły i zdjęcia Hoshi pobiera przez API. Wtyczka nie otrzymuje klucza API. Hoshi czyta `../python/data/inbox.sqlite3`, a własne potwierdzenia generowania zapisuje w `data/hoshi.sqlite3`. Nie zmienia statusów w kolejce odbiornika. Ten sam `request_id` nie jest generowany ponownie. Nowe wysłanie po odświeżeniu panelu może mieć nowe `request_id` i tworzyć nowy wydruk. Ręczne generowanie pozwala świadomie ponowić wydruk.

Potwierdzenie oznacza wygenerowanie pliku, nie fizyczne wydrukowanie na drukarce. Błąd odczytu pozostawia paczkę do ponowienia. Automatyczny odbiór zatrzymuje się po błędzie; popraw konfigurację i włącz go ponownie. Po zamknięciu programu odbieranie przestaje działać.

## Zapamiętywanie klucza

Klucz jest szyfrowany przez Windows DPAPI dla bieżącego użytkownika i zapisany w `data/api-key.dpapi`. Następne uruchomienia odczytują go automatycznie. To jednorazowa konfiguracja na każdym koncie Windows, a nie wspólny klucz zaszyty w programie. Kopiowanie zaszyfrowanego pliku na inny komputer lub konto nie jest sposobem dystrybucji. Administrator może raz przygotować każde stanowisko.

Źródłowy plik z kluczem nie jest potrzebny do późniejszego działania; program go nie usuwa. Folder `data/` jest pomijany przez Git i zawiera też wydruki z danymi klientów. DPAPI chroni klucz, nie same wydruki. Aplikacje działające jako ten sam użytkownik Windows mogą korzystać z jego DPAPI. Klucz nie trafia do raportów, HTML, rozszerzenia ani adresów URL. Zablokowano przekierowania HTTP z nagłówkiem autoryzacji.

## Uprawnienia

Dokładna lista i wyniki prób: [API-VERIFICATION.md](API-VERIFICATION.md). Obecny klucz poprawnie wykonał wszystkie sprawdzone odczyty. Nie potrzeba uprawnień do zapisu zamówień, wystawiania faktur, potwierdzania płatności ani przesyłania zdjęć.

## Polecenia

Uruchamiaj w folderze `hoshi`, używając `python` lub `py -3`:

```powershell
python hoshi.py setup --key-file "D:\sciezka\klucz.txt"
python hoshi.py orders 1084 1083 --open
python hoshi.py sample --limit 8
python hoshi.py queue
```

`sample` służy do ograniczonego testu API, maksymalnie 20 zamówień. Każdy wydruk ma obok raport `.report.json` z liczbami i wynikami HTTP, bez nazwisk, NIP-ów i klucza. Wydruki i zdjęcia działają offline po wygenerowaniu. Zdjęcia są buforowane na 24 godziny, zamówienia pobierane na nowo. Dane z raportu/HTML są stanem w momencie pobrania, nie podglądem na żywo.

## Zakres wczesnej wersji

- Obsługuje sklep `kartony24h.com`; adres API jest ustalony w programie.
- Pokazuje źródło, rzeczywiste konto sprzedawcy, żądanie faktury, NIP, płatności, klienta, dostawę, uwagi, produkty, ilości i zdjęcia.
- W próbce API zwracało `e_invoice` mimo opisu `e` w dokumentacji. Obsługujemy oba kody, `invoice`, `y` i `n`. Nie wywnioskujemy faktury z samego NIP-u.
- „Allegro Finanse” jest właściwą nazwą płatności i jest wyświetlane dokładnie tak, jak zwraca API, bez dodatkowego typu transakcji.
- Status płatności jest jawnie opisany jako wartość API. `pending` z bramki płatności nie jest zamieniane na „opłacone”; kod `y` z zamówienia również nie jest interpretowany bez udokumentowanej semantyki. Nie obliczamy statusu całego zamówienia na podstawie jednej wpłaty.
- Kwota pobrania pozostaje do weryfikacji; ta wersja nie wylicza jej automatycznie z wartości zamówienia. Przypadki pobrania i wpłat częściowych wymagają dodatkowych próbek.
- Zdjęcia pobieramy tylko z HTTPS domeny sklepu, bez klucza API. Nieobsługiwane hosty lub brak zdjęcia dają widoczny opis „Brak zdjęcia”.
- To karta magazynowa zawierająca także uwagi wewnętrzne, nie faktura ani dokument dla klienta.
- Nie ma cichego drukowania, instalatora EXE ani automatycznego uruchamiania z Windows.

## Weryfikacja

W folderze `hoshi`:

```powershell
python -m unittest discover -s tests -p test_hoshi.py -v
```

12 testów obejmuje DPAPI, braki zamówień, fakturę, rozdzielenie konta klienta i sprzedawcy, status płatności, escapowanie HTML, ograniczenie odczytów i hostów obrazów, porcjowanie zapytań oraz deduplikację i ponawianie kolejki. DPAPI trzeba testować na zwykłym koncie Windows; piaskownica Codex nie ma dostępu do jego magazynu.

Rzeczywisty test 1.10.2026: osiem zamówień, siedem różnych produktów, wszystkie zdjęcia pobrane; osiem kart na dwóch stronach A4 (po cztery). Zweryfikowano render PDF i otwieranie okna Tkinter z odczytem zapisanego klucza. Nie wykonano fizycznego druku ani pełnego testu kliknięcia w rozszerzeniu dla nowej paczki; kolejkę sprawdzono na izolowanej bazie testowej.
