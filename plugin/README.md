# Deutsche Rechtsprechung — Claude Code Plugin

Ein Claude Code Plugin, das Zugriff auf deutsche Gerichtsentscheidungen
(BVerfG, BGH, BVerwG, BFH, BAG, BSG, BPatG ab 2010) bietet.

## Installation

In Claude Code (CLI, Web oder Cowork):

```
/plugin marketplace add MansKos/deutsche-rechtsprechung-mcp
/plugin install deutsche-rechtsprechung
```

## Nutzung

Nach der Installation einfach den Skill aufrufen:

```
/deutsche-rechtsprechung:rechtsprechung Haftung bei Autounfall auf Privatparkplatz
```

Oder Claude direkt fragen — die MCP-Tools stehen automatisch zur Verfügung:

> "Suche nach BGH-Urteilen zu § 823 BGB Schadensersatz"

## Was passiert beim ersten Start?

Beim ersten Aufruf wird die SQLite-Datenbank (~2 GB) einmalig heruntergeladen.
Danach funktioniert alles offline. Die Datenbank wird im Plugin-Datenverzeichnis
gespeichert und bleibt auch bei Plugin-Updates erhalten.

## Enthaltene Komponenten

- **Skill**: `/deutsche-rechtsprechung:rechtsprechung` — Juristische Recherche mit strukturierter Analyse
- **MCP-Server**: `search_decisions` und `get_decision_by_doknr` Tools
- **Auto-Setup**: Datenbank wird automatisch heruntergeladen

## Für Entwickler

Plugin lokal testen:

```bash
claude --plugin-dir ./plugin
```
