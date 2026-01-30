# Rohlik Voice Assistant - Progress Report v1.0

**Datum:** 30. ledna 2026  
**Stav:** Integrace nainstalována, řešíme načtení Lovelace karty

---

## Přehled projektu

Hlasový asistent pro nakupování na Rohlik.cz integrovaný do Home Assistant. Uživatel mluví do mikrofonu na tabletu, AI zpracuje požadavek a přidá produkty do košíku na Rohlíku.

## Architektura

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Tablet s HA    │     │  Home Assistant      │     │  External APIs  │
│  Companion App  │     │  Green               │     │                 │
├─────────────────┤     ├──────────────────────┤     ├─────────────────┤
│                 │     │                      │     │                 │
│  Mikrofon  ─────┼────►│  WebSocket Proxy ────┼────►│  OpenAI         │
│                 │     │       │              │     │  Realtime API   │
│                 │     │       │              │     │  (gpt-4o-mini)  │
│                 │     │       ▼              │     │                 │
│  Reproduktor◄───┼─────│  Rohlik MCP Client ──┼────►│  Rohlik MCP     │
│                 │     │                      │     │  Server         │
│  Lovelace Card  │     │                      │     │  (mcp.rohlik.cz)│
│  (UI)           │     │                      │     │                 │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
```

## Technologie

- **LLM:** OpenAI GPT-4o-mini Realtime API (audio-to-audio)
- **Rohlik API:** Oficiální MCP server (https://mcp.rohlik.cz/mcp)
- **Protokol:** Server-Sent Events (SSE) pro MCP, WebSocket pro Realtime API
- **Frontend:** Custom Lovelace karta (JavaScript)
- **Backend:** Home Assistant Custom Integration (Python)

## Struktura projektu

```
rohlik_mco/
├── custom_components/
│   └── rohlik_voice/
│       ├── __init__.py          # HA integration setup
│       ├── manifest.json        # HA metadata
│       ├── const.py             # Konstanty (URLs, timeouts)
│       ├── config_flow.py       # UI pro zadání credentials
│       ├── mcp_client.py        # Rohlik MCP klient (SSE)
│       ├── realtime_api.py      # OpenAI Realtime API handler
│       ├── tools.py             # AI nástroje pro function calling
│       ├── websocket_api.py     # WebSocket endpoint pro frontend
│       ├── strings.json         # UI texty
│       └── translations/
│           ├── cs.json          # Čeština
│           └── en.json          # Angličtina
├── www/
│   └── rohlik-voice-card.js     # Lovelace karta (mikrofon UI)
├── hacs.json                    # HACS metadata
├── README.md                    # Dokumentace
└── progress_1.0.md              # Tento soubor
```

## Klíčové soubory a jejich funkce

### 1. `mcp_client.py` - Komunikace s Rohlíkem

```python
# Klíčové části:
- Accept header: "application/json, text/event-stream"
- Parsování SSE odpovědí (event: message\ndata: {...})
- Metody: search_products, add_to_cart, get_cart, remove_from_cart, etc.
```

**Důležité:** Rohlik MCP používá SSE protokol, ne standardní HTTP JSON.

### 2. `realtime_api.py` - OpenAI Voice AI

```python
# Klíčové části:
- WebSocket spojení s OpenAI Realtime API
- Model: gpt-4o-mini-realtime-preview
- Audio formát: PCM16, 24kHz
- Function calling pro Rohlik nástroje
```

### 3. `tools.py` - Definice AI nástrojů

```python
# Dostupné nástroje:
- search_products(keyword) - vyhledání produktů
- add_to_cart(product_id, quantity) - přidání do košíku
- get_cart() - zobrazení košíku
- remove_from_cart(product_id) - odebrání z košíku
- update_cart_item(product_id, quantity) - změna množství
- clear_cart() - vyprázdnění košíku
```

### 4. `rohlik-voice-card.js` - Uživatelské rozhraní

```javascript
// Funkce:
- Velké tlačítko mikrofonu (touch/click)
- Nahrávání audio a streaming do HA
- Přehrávání audio odpovědí
- Zobrazení přepisu konverzace
- Zobrazení stavu košíku
```

## Credentials a bezpečnost

Credentials jsou uloženy **šifrovaně** v Home Assistant:
- Rohlik email a heslo
- OpenAI API klíč

Uložení: `config/.storage/core.config_entries` (šifrováno)

## Aktuální stav (v1.0)

### ✅ Hotovo:
1. Rohlik MCP klient s SSE protokolem
2. OpenAI Realtime API handler
3. Home Assistant custom integration
4. Config flow pro zadání credentials
5. WebSocket API pro frontend
6. Lovelace karta (JavaScript)
7. Česká a anglická lokalizace
8. Credentials validace funguje
9. Repozitář na GitHubu

### 🔄 Probíhá:
1. **Lovelace karta se nenačítá** - "Custom element doesn't exist"
   - Soubory jsou v `www/` a `custom_components/`
   - Resource je přidaný
   - Pravděpodobně potřeba restart HA nebo cache clear

### ❌ Čeká:
1. Testování hlasového vstupu
2. Testování přidávání do košíku
3. Optimalizace audio streamingu
4. Error handling

## Troubleshooting - Lovelace karta

### Problém: "Custom element doesn't exist: rohlik-voice-card"

**Kontrolní seznam:**
1. [ ] Soubor existuje: `config/www/rohlik-voice-card.js`
2. [ ] Resource přidán: Settings → Dashboards → Resources
   - URL: `/local/rohlik-voice-card.js`
   - Type: JavaScript Module
3. [ ] Home Assistant restartován
4. [ ] Hard refresh prohlížeče (Ctrl+Shift+R)
5. [ ] Test URL: `http://HA_IP:8123/local/rohlik-voice-card.js` zobrazí JS kód

**Debug:**
- F12 → Console → hledej chyby s "rohlik"
- F12 → Network → filtruj "rohlik" → zkontroluj status

## API Reference

### Rohlik MCP Server

**URL:** `https://mcp.rohlik.cz/mcp`

**Headers:**
```
Content-Type: application/json
Accept: application/json, text/event-stream
rhl-email: user@example.com
rhl-pass: password
```

**Formát požadavku:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": {"keyword": "mléko"}
  }
}
```

**Formát odpovědi (SSE):**
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}
```

### OpenAI Realtime API

**URL:** `wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview`

**Audio formát:** PCM16, 24000 Hz, mono

## GitHub Repository

**URL:** https://github.com/isildur77/rohlik_mco

**Klonování:**
```bash
git clone git@github.com:isildur77/rohlik_mco.git
```

## Příkazy pro testování

### Test Rohlik MCP (curl):
```bash
curl -X POST https://mcp.rohlik.cz/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "rhl-email: YOUR_EMAIL" \
  -H "rhl-pass: YOUR_PASSWORD" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Test search:
```bash
curl -X POST https://mcp.rohlik.cz/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "rhl-email: YOUR_EMAIL" \
  -H "rhl-pass: YOUR_PASSWORD" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_products","arguments":{"keyword":"mléko"}}}'
```

## Další kroky

1. **Vyřešit načítání Lovelace karty**
   - Zkontrolovat přesnou cestu k souboru
   - Ověřit syntax JS souboru
   - Restartovat HA

2. **Otestovat kompletní flow**
   - Mikrofon → AI → Rohlik → Odpověď

3. **Přidat error handling**
   - Timeout handling
   - Offline mode
   - User-friendly error messages

4. **Optimalizace**
   - Audio buffer management
   - Latency reduction
   - Memory usage

---

**Poznámka:** Tento dokument slouží jako checkpoint pro pozdější návrat k projektu.
