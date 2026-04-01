# Deutsche Rechtsprechung — Claude Desktop Extension

Eine Desktop Extension für Claude Desktop, die Zugriff auf deutsche Gerichtsentscheidungen
(BVerfG, BGH, BVerwG, BFH, BAG, BSG, BPatG ab 2010) bietet.

## Installation

1. Lade die Datei `deutsche-rechtsprechung.mcpb` herunter
2. Doppelklicke darauf — Claude Desktop installiert die Extension automatisch
3. Beim ersten Gespräch wird die Datenbank einmalig heruntergeladen (~2 GB)

## Nutzung

Einfach Claude eine juristische Frage stellen, z.B.:
- "Suche nach BGH-Urteilen zu § 823 BGB"
- "Finde Entscheidungen zum Thema Mietminderung"
- "Was sagt die Rechtsprechung zur Haftung bei Autounfällen?"

## Build

```bash
# mcpb CLI installieren (einmalig)
npm install -g @anthropic-ai/mcpb

# Extension bauen
cd desktop-extension
mcpb pack
```

Dies erstellt `deutsche-rechtsprechung.mcpb` im aktuellen Verzeichnis.
