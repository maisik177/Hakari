<!-- Autor: Maksymilian Dyla, firma Cart-pack -->
# Hakari — pakiet CRX i klucz podpisujący

- Wersja: 0.4.1.
- Identyfikator podpisanej wtyczki: `pglgeejbnomibglbkiimpfcbdmbaihdk`.
- `Hakari-wtyczka.crx`: podpisana paczka CRX3, zawierająca wyłącznie 17 plików wtyczki.
- `Hakari-wtyczka.pem`: lokalny prywatny klucz do podpisywania kolejnych wersji z tym samym identyfikatorem; nie jest częścią repozytorium.

Klucz pozostaje lokalnie i jest wykluczony z Git przez .gitignore. Nie udostępniaj klucza odbiorcom wtyczki. Zachowaj dodatkową bezpieczną kopię.

## Kolejna wersja

1. Zwiększ `version` w `manifest.json` i przygotuj folder zawierający wyłącznie pliki wtyczki (bez tego folderu `release`, testów, Pythona i Hoshi).
2. W Chrome otwórz `chrome://extensions`, włącz tryb dewelopera i wybierz „Spakuj rozszerzenie”.
3. Wskaż folder wtyczki oraz istniejący plik `Hakari-wtyczka.pem` w polu klucza prywatnego. Nie generuj nowego klucza.
4. Zastąp plik CRX nową paczką, zachowując ten sam PEM.

Samo przechowywanie CRX i PEM na GitHubie nie włącza automatycznych aktualizacji. Projekt nie ma skonfigurowanego serwera aktualizacji. W Chrome na Windows/macOS instalacja rozszerzeń spoza Chrome Web Store podlega ograniczeniom i wymaga odpowiednich zasad organizacji. Do lokalnego użycia można nadal załadować folder rozpakowanej wtyczki.

Dokumentacja: https://developer.chrome.com/docs/extensions/how-to/distribute

## Hoshi i receiver

Hakari-hoshi-receiver.zip zawiera Hoshi, odbiornik Python, skrypty startowe, dokumentację oraz ich testy. Rozpakuj całość przed uruchomieniem. Archiwum nie zawiera danych roboczych ani kluczy połączenia.


