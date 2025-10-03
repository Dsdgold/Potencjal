 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/README.md
index 0000000000000000000000000000000000000000..564f43ae03f9a3bf6c8a634da1d6ac488aa5fef3 100644
--- a//dev/null
+++ b/README.md
@@ -0,0 +1,30 @@
+# Potencjał klienta – narzędzie offline
+
+Ten repozytorium zawiera pojedynczy plik HTML implementujący narzędzie do szybkiej oceny potencjału klienta z wykorzystaniem heurystyk oraz ręcznie wklejanych danych OSINT.
+
+## Uruchomienie
+
+1. Otwórz plik `mvp_osint_launcher_szybkie_sprawdzenie_potencjalu_html.html` w przeglądarce (dwuklik lub `open` / `xdg-open`).
+2. Wpisz nazwę firmy lub NIP, opcjonalnie miasto i wartość aktualnego koszyka.
+3. Skorzystaj z przycisków wyszukiwania, aby otworzyć dodatkowe karty OSINT.
+4. Wklej znalezione dane w sekcję „Wklej dane znalezione w sieci” i kliknij „Zastosuj wklejkę do profilu”, aby natychmiast przeliczyć scoring.
+
+## Powiązanie z GitHubem
+
+Repozytorium można łatwo połączyć z istniejącym projektem na GitHubie, korzystając ze skryptu pomocniczego `scripts/setup_github_remote.sh`.
+
+```bash
+# nadaj url swojego repozytorium oraz (opcjonalnie) nazwę głównej gałęzi
+scripts/setup_github_remote.sh git@github.com:twoja-firma/potencjal.git main
+
+# połączenie gotowe – wypchnij zmiany
+git push -u origin work
+```
+
+Skrypt:
+- dodaje lub aktualizuje zdalne `origin`,
+- próbuje pobrać wskazaną gałąź (ignorując brak),
+- ustawia śledzenie bieżącej gałęzi względem zdalnej,
+- informuje jak wypchnąć zmiany.
+
+Dzięki temu repozytorium pozostaje zsynchronizowane z GitHubem przy minimalnym nakładzie pracy.
 
EOF
)
