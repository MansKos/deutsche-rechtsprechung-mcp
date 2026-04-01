# Rechtsprechung MCP Server

Ein [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/spec) Server, der die Daten von [Rechtsprechung im Internet](https://www.rechtsprechung-im-internet.de) (Entscheidungen des Bundesverfassungsgerichts, der obersten Gerichtshöfe des Bundes sowie des Bundespatentgerichts ab dem Jahr 2010) durchsuchbar und für LLMs (Large Language Models) zugänglich macht.

## Projektübersicht

Dieses Projekt stellt eine Schnittstelle bereit, über die KI-Agenten und Anwendungen auf eine umfangreiche Datenbank deutscher Rechtsprechung zugreifen können. Es besteht aus drei Hauptkomponenten:

1.  **MCP Server**: Der Kern des Projekts. Ein FastMCP-Server, der Tools zur Suche und zum Abruf von Volltexten bereitstellt.
2.  **Claude Desktop Extension**: Eine `.mcpb`-Datei für One-Click-Installation in Claude Desktop (ideal für Nicht-Entwickler).
3.  **Claude Code Integration**: Skill + MCP-Konfiguration für `/rechtsprechung`-Befehl in Claude Code.
4.  **Data Preprocessing**: Eine Pipeline, um Urteile von "Rechtsprechung im Internet" herunterzuladen, zu bereinigen und in ein durchsuchbares Format zu konvertieren.
5.  **Beispiel-Agent**: Ein Google ADK Agent, der demonstriert, wie man den MCP Server nutzen kann, um juristische Fragestellungen zu beantworten.

## 1. MCP Server

Der Server läuft in einem Docker-Container und nutzt OpenSearch als Backend für schnelle und flexible Volltextsuchen.

### Funktionen (Tools)

*   `search_decisions(query: str, limit: int)`: Sucht nach Urteilen basierend auf Text, Aktenzeichen oder Normen.
*   `get_decision_by_doknr(doknr: str)`: Ruft den vollständigen Text (Leitsätze, Gründe, Metadaten) eines spezifischen Urteils ab.

### Technologie

*   **Python**: Implementierung des Servers mit `mcp.server.fastmcp`.
*   **Such-Backend (wählbar)**:
    *   **SQLite FTS5** (Standard): Leichtgewichtig, keine externen Dienste nötig. Nur Python + SQLite.
    *   **OpenSearch**: Mächtiger, aber benötigt einen laufenden OpenSearch-Container (~2–4 GB RAM).
*   **Docker Compose**: Optionale Orchestrierung.

### Starten des Servers

#### Option A: SQLite (leichtgewichtig, empfohlen zum Einstieg)

**Mit Docker:**
```bash
cd mcp
docker-compose -f docker-compose.sqlite.yml up --build
```

**Ohne Docker (lokal):**
```bash
cd mcp
pip install -r requirements.txt
# 1. Daten importieren (nur beim ersten Mal)
python src/ingest_sqlite.py
# 2. Server starten
python src/server.py
```

#### Option B: OpenSearch (Original)

```bash
cd mcp
SEARCH_BACKEND=opensearch docker-compose up --build
```

Der Server ist anschließend unter `http://localhost:8002/mcp` erreichbar. Die Datenbank wird beim ersten Start automatisch initialisiert.

#### Option C: Claude Desktop Extension (für Nicht-Entwickler)

Die einfachste Methode — keine Programmierkenntnisse erforderlich:

1. Lade `deutsche-rechtsprechung.mcpb` aus den [Releases](https://github.com/MansKos/deutsche-rechtsprechung-mcp/releases) herunter
2. Doppelklicke die Datei — Claude Desktop installiert alles automatisch
3. Die Datenbank wird beim ersten Gespräch einmalig heruntergeladen (~2 GB)

Danach einfach Claude fragen: *"Suche nach BGH-Urteilen zu § 823 BGB"*

Siehe `desktop-extension/README.md` für Build-Anweisungen.

#### Option D: Claude Code Plugin (empfohlen für Claude Code / Cowork)

Kein Terminal nötig — direkt in Claude Code eingeben:

```
/plugin marketplace add MansKos/deutsche-rechtsprechung-mcp
/plugin install deutsche-rechtsprechung
```

Dann einfach nutzen:
```
/deutsche-rechtsprechung:rechtsprechung Haftung bei Autounfall
```

Das Plugin installiert den MCP-Server und den `/rechtsprechung`-Skill automatisch.
Die Datenbank wird beim ersten Aufruf heruntergeladen.

Siehe `plugin/README.md` für Details.

#### Option E: Claude Code (Repo klonen)

Alternativ für Entwickler — Repo klonen und direkt loslegen:

```bash
git clone https://github.com/MansKos/deutsche-rechtsprechung-mcp.git
cd deutsche-rechtsprechung-mcp
# Claude Code öffnen und den Skill nutzen:
# /rechtsprechung Haftung bei Autounfall
```

Der MCP-Server wird automatisch über `.claude/mcp.json` konfiguriert.

#### Option E: uvx (für Claude Desktop manuell)

In der Claude-Desktop-Konfiguration (`claude_desktop_config.json`) hinzufügen:

```json
{
  "mcpServers": {
    "deutsche-rechtsprechung": {
      "command": "uvx",
      "args": ["deutsche-rechtsprechung-mcp"]
    }
  }
}
```

Voraussetzung: [uv](https://docs.astral.sh/uv/) installiert (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

## 2. Data Preprocessing

Bevor der Server nützlich ist, müssen Daten ingestiert werden. Die Skripte im Ordner `prepare_data/` kümmern sich um die Beschaffung und Aufbereitung.

*   **Quelle**: [Rechtsprechung im Internet](https://www.rechtsprechung-im-internet.de/) (Open Data).
*   **Prozess**:
    1.  Links extrahieren (`extract_links.py`).
    2.  XML-Daten herunterladen (`download_files.py`).
    3.  Entpacken (`extract_zips.py`).
    4.  Konvertierung zu Markdown für optimale LLM-Lesbarkeit (`convert_all_to_md.py`).

Detaillierte Anweisungen finden sich in `prepare_data/README.md`.

## 3. Beispiel-Agent (Google ADK)

Im Ordner `google-adk-agent/` befindet sich ein Referenz-Agent, der zeigt, wie man den MCP-Server in eine Anwendung integriert.

*   **Framework**: Google Agent Development Kit (ADK).
*   **Modell**: Gemini 2.5 Flash / Gemini 3 Pro Preview.
*   **Funktion**: Der Agent analysiert Sachverhalte, sucht selbstständig passende Urteile und gibt eine rechtliche Einschätzung ab.

Siehe `google-adk-agent/agent/README.md` für Details zur Einrichtung.

## Voraussetzung

*   Python 3.10+ (SQLite ist in der Standardbibliothek enthalten)
*   Docker & Docker Compose (nur für OpenSearch-Backend oder Docker-Deployment)
*   Zugriff auf Gemini API (für den Agenten)

## Lizenz

Dieses Projekt ist unter der [MIT License](LICENSE) lizenziert. Die Daten stammen vom Bundesministerium der Justiz und dem Bundesamt für Justiz.
