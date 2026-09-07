# IPTV Dream 8.0.1

Wydanie naprawcze po pełnym przeglądzie wersji 8.0.0.

Najważniejsze poprawki:

- naprawiony eksport kanałów pokazywanych jako `N/A`;
- naprawiony czarny obraz dla nierozwiązanych linków MAC/Stalker (`127.0.0.1`);
- lokalne komendy portalu są rozwiązywane także na listach powyżej 400 kanałów;
- bezpieczne kodowanie URL i nazw w referencjach Enigma2;
- poprawione raportowanie eksportu, backup i czyszczenie `bouquets.tv`;
- grupowanie bukietów według źródła oraz opcja usunięcia wszystkich starych bukietów jednym wyborem;
- brak kolizji wielu list M3U/Xtream/MAC oraz brak loginu/MAC w nazwach plików;
- WebIF automatycznie wybiera wolny port, gdy 9999 jest zajęty;
- poprawki XML EPG, piconów, logów, instalatora i aktualizatora;
- automatyczne testy regresyjne na GitHub Actions.

Walidacja: 10/10 testów, pełny `compileall`, kontrola składni instalatora oraz weryfikacja zawartości i powtarzalnego buildu IPK.

Instalacja z `/tmp`:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_8.0.1_all.ipk
init 4
sleep 2
init 3
```

Po aktualizacji warto ponownie wyeksportować bukiety. Istniejących ustawień i zapisanych portali instalacja nie usuwa.
