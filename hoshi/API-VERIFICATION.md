# Weryfikacja API IdoSell — Hoshi

Data: 1 października 2026, Europe/Warsaw. Sklep: `kartony24h.com`. API Admin v8. Wyłącznie odczyty; POST został użyty tylko w metodzie wyszukiwania. Nie modyfikowano konfiguracji uprawnień ani danych sklepu.

## Funkcje do zaznaczenia dla klucza Hoshi

W **Ustawienia → Dostęp → klucze API Admin** należy udostępnić poniższe operacje. Identyfikatory operacji i ścieżki pochodzą ze specyfikacji sklepu; tekst etykiet w panelu może się różnić. Przy ograniczeniu hostów/IP uwzględnij publiczny adres wyjściowy stanowiska Hoshi.

| Operacja (operationId) | Metoda i ścieżka po `/api/admin/v8/` | Cel | Próba |
|---|---|---|---|
| `orders/orders/get` | GET `orders/orders` | Zamówienie, produkty, ilości, faktura, NIP, uwagi, dostawa, wpłaty | HTTP 200, 8 zamówień |
| `orders/auctionDetails/get` | GET `orders/auctionDetails` | Konto sprzedawcy Allegro, odrębne od konta kupującego | HTTP 200, 8 zamówień |
| `products/products/get` | GET `products/products` | Adres miniatury i zdjęć produktu | HTTP 200, 7 produktów |
| `payments/payments/get` | GET `payments/payments` | Szczegóły i status konkretnej transakcji | HTTP 200, 8 transakcji |
| `orders/orders/search/post` | POST `orders/orders/search` | Sprawdzenie klucza przy imporcie, próbka diagnostyczna | HTTP 200 |
| `payments/forms/get` | GET `payments/forms` | Opcjonalny słownik nazw form płatności; diagnostyka, niepotrzebny do zwykłego wydruku | HTTP 200 |

**Obecny klucz ma działający dostęp do wszystkich powyższych operacji.** Nie trzeba na potrzeby tej wersji rozszerzać jego praw. Nie sprawdzano zapisu i nie wnioskujemy, że klucz ma tylko prawa odczytu. Nie udostępniaj Hoshi metod PUT, DELETE ani POST modyfikujących sklep. Odczyt flagi faktury nie wymaga prawa wystawiania faktur. Zdjęcia nie wymagają prawa zapisu `products/images`.

## Co faktycznie udało się odczytać

Próbka: 8 zamówień, 9 pozycji, 7 różnych produktów. To mała próbka, nie pełny audyt historii sklepu.

| Informacja | Pole / metoda | Wynik |
|---|---|---|
| Kanał | `orderDetails.orderSourceResults.orderSourceDetails.orderSourceName` | Allegro oraz Allegro.pl Business |
| Konto sprzedawcy | `orders/auctionDetails → auctions[].auctionsAccountLogin` | 8/8; dwa różne konta sprzedawcy |
| Żądanie faktury | `orderDetails.clientRequestInvoice` | 8/8 rozpoznane: `e_invoice` albo `n` |
| NIP | `clientResult.clientBillingAddress.clientNip` | obecny w 7/8; brak w zamówieniu bez żądania faktury |
| Forma płatności | `orderDetails.prepaids[].payformName` | 8/8: `Allegro Finanse` |
| Szczegóły transakcji | `payments/payments → result` | kwota, waluta, status, ID formy, identyfikator zewnętrzny, dziennik zdarzeń |
| Zdjęcie | `products/products → results[].productIcon` / `productImages` | 7/7 produktów; wszystkie obrazy poprawnie załadowane w wydruku |
| Dostawa / punkt odbioru | `orderDetails.dispatch`, `clientResult.clientPickupPointAddress` | dostępne; zakres zależy od zamówienia |
| Klient, adresy, login | `clientResult`, `orderDetails.auctionInfo` | dostępne; wydruk ogranicza się do danych przydatnych przy kompletacji |
| Uwagi i towary | `orderDetails`, `productsResults` | nazwy, kody, ilości, rozmiary, ceny, VAT, waga, uwagi klienta i wewnętrzne |

## Istotne ograniczenia / rozbieżności

1. **Nazwa płatności: Allegro Finanse.** W badanych rekordach API zwraca tę nazwę i jest ona zgodna z wymaganiami wydruku. Nie jest potrzebne dodatkowe rozróżnienie sposobów finansowania ani integracja z API Allegro. Wydruk nie pokazuje technicznego typu transakcji (`paymentType`).
2. **IdoPay znajduje się w słowniku jako ID 29**, ale w próbce nie było zamówienia opłaconego przez IdoPay. Nie potwierdzono działania na takim rzeczywistym zamówieniu. Kod zachowuje nazwę formy zwróconą dla dowolnej wpłaty.
3. **Statusy:** zamówienia zwracały `paymentStatus: y`, a bramka szczegółów transakcji `status: pending`. Specyfikacja pola zamówienia nie definiuje znaczenia kodu `y`. Wczesna wersja pokazuje literalny status API i nie oznacza zamówień jako opłaconych. Wymaga to dalszego porównania z potwierdzonym stanem księgowania przed automatyzacją decyzji magazynowych.
4. **Faktura:** specyfikacja opisuje `e`, rzeczywiste odpowiedzi zawierały `e_invoice`. Oba są obsługiwane. Nieznany kod jest widoczny jako brak rozpoznanych danych, nigdy automatycznie „NIE”.
5. **Parametr tablicowy aukcji:** zapis powtórzonych parametrów `orders` zgodny z `explode=true` w specyfikacji zwrócił tylko jedno zamówienie. W Hoshi wykonujemy po jednym odczycie `orders/auctionDetails` na zamówienie i dopasowujemy wynik po numerze. Test potwierdził komplet 8/8.
6. Próbka potwierdza dwa konta Allegro. Nie testowano eBay, innych marketplace'ów, pobrania, rozliczeń częściowych, zwrotów ani anulowań. Płatności wyświetlamy osobno, bez wnioskowania o rozliczeniu całości.

## Dowody i dokumentacja

Weryfikację wykonano lokalnie na rzeczywistych danych. Wydruki, odpowiedzi API, dane klientów i klucz nie są częścią repozytorium. Program zapisuje nowe wydruki i raporty `.report.json` w pomijanym przez Git folderze `data/wydruki/`. Raport zawiera wyniki HTTP, statystyki i czas pobrania, bez klucza i danych klientów.

- [Specyfikacja OpenAPI sklepu, API Admin v8](https://kartony24h.com/api/doc/admin/v8/json)
- [IdoSell — klucze dostępowe i ograniczenia dostępu](https://pomoc.idosell.com/wyglad-i-konfiguracja/api/klucze-dostepowe-do-api-admin)
- [IdoSell — wprowadzenie do API](https://idosell.readme.io/docs/getting-started)
