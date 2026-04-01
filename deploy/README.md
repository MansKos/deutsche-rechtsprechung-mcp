# Gehosteter MCP-Server — Deployment-Anleitung

Dieser Ordner enthält alles, um den Rechtsprechung-MCP-Server als öffentlichen
HTTP-Endpunkt zu deployen. Damit können Nutzer **ohne Installation** auf die
Urteilsdatenbank zugreifen — direkt aus Claude Desktop, Cowork oder jeder
anderen MCP-fähigen Anwendung.

## Warum ein gehosteter Server?

| Client | Lokaler MCP (stdio) | Gehosteter MCP (HTTP) |
|--------|--------------------|-----------------------|
| Claude Desktop Chat | ✅ (.mcpb) | ✅ |
| Claude Cowork | ❌ (Bug: VM-Isolation) | ✅ |
| Claude Code | ✅ (Plugin) | ✅ |
| claude.ai Web | ❌ | ❌ |

**Fazit:** Ein gehosteter Server ist der einzige Weg, der überall funktioniert
(außer claude.ai Web, das gar kein MCP kann).

## Quick Deploy

### Option 1: fly.io (empfohlen)

```bash
# 1. fly CLI installieren (einmalig)
curl -L https://fly.io/install.sh | sh

# 2. Einloggen
fly auth login

# 3. App erstellen & deployen
cd deploy
fly launch --copy-config --yes
fly volumes create rechtsprechung_data --region fra --size 5

# 4. Deployen
fly deploy

# 5. Die URL ist nun:
#    https://deutsche-rechtsprechung-mcp.fly.dev/mcp
```

**Kosten:** ~3-5 USD/Monat (shared-cpu-1x, 512 MB RAM, 5 GB Disk).
Auto-Suspend wenn nicht genutzt → Kosten sinken auf fast 0.

### Option 2: Render.com

1. Fork dieses Repos auf GitHub
2. Gehe zu [render.com](https://render.com) → "New" → "Blueprint"
3. Verbinde dein GitHub-Repo
4. Render erkennt `render.yaml` automatisch
5. "Apply" klicken → läuft

**Kosten:** ~7 USD/Monat (Starter Plan mit Persistent Disk).

### Option 3: Beliebiger VPS

```bash
# Auf deinem Server (z.B. Hetzner, DigitalOcean)
cd deploy
docker build -t rechtsprechung-mcp .
docker run -d \
  -p 8002:8002 \
  -v rechtsprechung-data:/data \
  --name rechtsprechung-mcp \
  --restart unless-stopped \
  rechtsprechung-mcp
```

Dann mit einem Reverse-Proxy (nginx, Caddy) + Let's Encrypt HTTPS einrichten.

## Für deine Freunde: So verbinden sie sich

### In Claude Desktop

1. Öffne Claude Desktop
2. Gehe zu **Settings** → **Developer** → **Edit Config**
3. Füge das hier ein:

```json
{
  "mcpServers": {
    "deutsche-rechtsprechung": {
      "url": "https://DEINE-URL.fly.dev/mcp"
    }
  }
}
```

4. Claude Desktop neustarten
5. Fertig — einfach Claude fragen: *"Suche nach BGH-Urteilen zu § 823 BGB"*

### In Claude Cowork

1. Öffne Cowork in Claude Desktop
2. Gehe zu **Customize** → **Connectors**
3. Klicke **"Add Connector"** → **"Custom MCP Server"**
4. Trage die URL ein: `https://DEINE-URL.fly.dev/mcp`
5. Fertig

### Anleitung für Nicht-Techniker (zum Weiterleiten)

> **So bekommst du Zugang zur Rechtsprechung-Suche:**
>
> 1. Öffne Claude Desktop
> 2. Klicke oben rechts auf ⚙️ (Einstellungen)
> 3. Klicke auf "Developer" → "Edit Config"
> 4. Es öffnet sich eine Datei. Ersetze den gesamten Inhalt durch:
>
> ```json
> {
>   "mcpServers": {
>     "deutsche-rechtsprechung": {
>       "url": "https://DEINE-URL.fly.dev/mcp"
>     }
>   }
> }
> ```
>
> 5. Speichere die Datei (Strg+S / Cmd+S)
> 6. Schließe Claude Desktop komplett und öffne es neu
> 7. Frage Claude jetzt z.B.: *"Suche nach Urteilen zum Thema Mietminderung bei Schimmel"*

## Sicherheit & Datenschutz

- Der Server enthält nur **öffentlich zugängliche** Gerichtsentscheidungen
- Keine personenbezogenen Daten werden verarbeitet
- Für den Produktiveinsatz: Zugriff per API-Key einschränken (siehe unten)

### Optional: API-Key-Schutz

Um den Zugriff einzuschränken, setze die Umgebungsvariable `API_KEY`:

```bash
fly secrets set API_KEY=dein-geheimer-schluessel
```

Dann in der Client-Config:
```json
{
  "mcpServers": {
    "deutsche-rechtsprechung": {
      "url": "https://DEINE-URL.fly.dev/mcp",
      "headers": {
        "Authorization": "Bearer dein-geheimer-schluessel"
      }
    }
  }
}
```
