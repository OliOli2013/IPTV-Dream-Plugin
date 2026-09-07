# Audyt IPTV Dream 8.0.1

Data: 2026-09-07  
Zakres: pakiet `enigma2-plugin-extensions-iptvdream_8.0.0_all.ipk`, kod gałęzi `main` repozytorium `OliOli2013/IPTV-Dream-Plugin`, eksport M3U/Xtream/MAC, EPG, picony, WebIF, aktualizator i pakowanie IPK.

## Wniosek

Zgłoszenie użytkownika było zasadne. W wersji 8.0.0 występowały dwie bezpośrednie regresje zgodne z objawami: pusta nazwa w pełnej referencji Enigma2 mogła dawać `N/A` na części image'ow, a literówka w rozpoznawaniu adresu loopback powodowała eksport nierozwiązanych linków MAC/Stalker i czarny ekran. Dodatkowo szybka ścieżka dla portali powyżej 400 kanałów pomijała rozwiązanie lokalnych komend.

## Najważniejsze ustalenia i poprawki

| Ważność | Ustalenie w 8.0.0 | Poprawka w 8.0.1 |
|---|---|---|
| Krytyczna | `#SERVICE` kończył się pustym polem nazwy | Nazwa kanału jest kodowana w referencji i nadal zapisywana w `#DESCRIPTION` |
| Krytyczna | Sprawdzano `128.0.0.1` zamiast `127.0.0.1` | Pełna detekcja `127/8`, `localhost`, `::1` i `0.0.0.0`, także z portem |
| Krytyczna | Duże portale MAC nie rozwiązywały lokalnych/nieprzezroczystych komend | Takie komendy zawsze przechodzą przez `create_link/get_link`; pomijane są tylko gotowe zdalne URL |
| Wysoka | Eksport zgłaszał sukces mimo błędu dopisania do `bouquets.tv` | Liczone są tylko rzeczywiście podpięte bukiety; błąd przerywa fałszywy sukces |
| Wysoka | Po zmianie nazwy źródła stare bukiety mogły pozostać obok nowych, a ekran usuwania grupował je po widocznej grupie | Metadana źródła, usuwanie pełnych zestawów i opcja usunięcia wszystkich bukietów jednym wyborem |
| Wysoka | Kilka źródeł M3U mogło nadpisywać te same pliki; nazwa Xtream zawierała login, MAC fragment adresu | Stabilne nazwy host + skrót SHA-1, bez loginu i adresu MAC |
| Średnia | Znaki sterujące mogły uszkodzić strukturę bukietu | Walidacja schematu URL, pojedyncza linia nazwy i bezpieczne kodowanie każdego pola referencji |
| Średnia | Backup indeksu mógł powstać dopiero po pierwszej modyfikacji; zostawały duplikaty i martwe wpisy | Jedna kopia przed eksportem oraz ostrożne czyszczenie tylko wpisów IPTV Dream |
| Średnia | Konflikt portu WebIF 9999 wyłączał funkcję | Automatyczny fallback na najbliższy wolny port i zapamiętanie faktycznego portu |
| Średnia | XML własnego EPG nie escapował `&`, `<`, `>` | Poprawne escapowanie i atomowy zapis |
| Średnia | Pobieranie piconu przy wyłączonym cache używało niezainicjalizowanego klucza; brak limitu pliku | Klucz jest zawsze tworzony, limit 5 MiB i limit bezpiecznych wymiarów obrazu |
| Niska | Instalator/updater mógł kopiować pliki testowe lub wydaniowe do tunera | Generyczne czyszczenie oraz allowlista runtime w budowaniu IPK |
| Niska | Logi mogły pozostawiać dane logowania w niektórych wariantach URL | Maskowanie userinfo, parametrów token/login i ścieżek Xtream |

## Walidacja

- 10/10 testów regresyjnych zakończonych powodzeniem na Pythonie 3.12.
- Test eksportu typów 4097 i 5002, nazw z dwukropkiem/Unicode, URL z query i już zakodowanymi znakami.
- Test braku `N/A`, zachowania URL po dekodowaniu oraz odrzucenia wieloliniowego wstrzyknięcia do bukietu.
- Test M3U z przecinkiem w cudzysłowie, `#EXTGRP`, Unicode i `tvg-id`.
- Test wymuszonego rozwiązania lokalnego linku MAC przy wyłączonym trybie masowego resolve.
- Test zajętego portu 9999 i startu WebIF na 10000.
- `compileall` wszystkich plików Python i kontrola składni `installer.sh`.
- Kontrola zawartości IPK, metadanych, uprawnień i braku plików developerskich w runtime.

## Granice audytu

Nie da się uczciwie zagwarantować działania "100%" dla każdego portalu IPTV bez danych dostępowych i testu na fizycznym tunerze. Portale Stalker bywają niestandardowe, a serwery EPG/piconów są zewnętrzne. Kod zabezpiecza znane warianty i usuwa odtworzone regresje, ale przed publicznym wydaniem zalecany jest krótki test terenowy na OpenATV i OpenPLi: po jednej liście M3U, Xtream i MAC (małej oraz powyżej 400 kanałów).

WebIF pozostaje celowo domyślnie wyłączony i nie ma logowania; powinien być uruchamiany wyłącznie w zaufanej sieci lokalnej. Aktualizator pobiera kod przez HTTPS z gałęzi `main`; krytyczne wydania warto dodatkowo publikować jako oznaczone tagi/releases.
