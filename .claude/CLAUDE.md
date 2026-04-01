# Deutsche Rechtsprechung MCP

Dieses Projekt stellt eine durchsuchbare Datenbank deutscher Gerichtsentscheidungen bereit.

## Verfügbare Befehle

- `/rechtsprechung <Anfrage>` — Suche nach Urteilen und erhalte eine juristische Analyse

## Beispiele

```
/rechtsprechung Haftung bei Autounfall auf Privatparkplatz
/rechtsprechung BGH-Urteile zu § 823 BGB Schadensersatz
/rechtsprechung Mietminderung wegen Schimmel
/rechtsprechung Kündigung in der Probezeit
```

## MCP-Tools

Der MCP-Server "deutsche-rechtsprechung" bietet zwei Tools:
- `search_decisions` — Volltextsuche nach Urteilen
- `get_decision_by_doknr` — Volltext eines Urteils abrufen

Die Datenbank enthält Entscheidungen von BVerfG, BGH, BVerwG, BFH, BAG, BSG und BPatG ab 2010.
