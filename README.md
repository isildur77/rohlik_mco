# Rohlik Voice Assistant pro Home Assistant

Hlasový asistent pro nakupování na Rohlik.cz přímo z Home Assistant dashboardu.

## Funkce

- **Hlasové ovládání** - Stiskni tlačítko mikrofonu a řekni co chceš koupit
- **Konverzace v češtině** - AI asistent rozumí a odpovídá česky
- **Správa košíku** - Přidávej, odebírej produkty, zobrazuj košík
- **Dotazy na produkty** - "Jaké mají mléka?" "Kolik stojí chléb?"

## Architektura

```
Tablet (HA App) → Home Assistant Green → OpenAI Realtime API
                                              ↕
                                      Rohlik MCP Server
```

- **Audio vstup/výstup**: Mikrofon a reproduktor tabletu
- **LLM**: OpenAI GPT-4o-mini Realtime (audio-to-audio)
- **Rohlik API**: Oficiální MCP server (https://mcp.rohlik.cz/mcp)

## Požadavky

- Home Assistant 2024.1+
- Home Assistant Companion App na tabletu (nebo webový prohlížeč)
- OpenAI API klíč s přístupem k Realtime API
- Účet na Rohlik.cz

## Instalace

### Krok 1: Nainstaluj HACS (pokud nemáš)

1. Jdi na https://hacs.xyz/docs/use/download/download
2. Pro HA Green: **Settings → Add-ons → Add-on Store → HACS → Install**
3. Restartuj Home Assistant
4. **Settings → Devices & Services → Add Integration → HACS**
5. Autorizuj přes GitHub

### Krok 2: Přidej Rohlik Voice

1. **HACS → Integrations → menu (3 tečky) → Custom repositories**
2. URL: `https://github.com/isildur77/rohlik_mco`
3. Kategorie: **Integration**
4. Klikni **Add**
5. Vyhledej "Rohlik Voice" → **Download**
6. Restartuj Home Assistant

### Krok 3: Nakonfiguruj integraci

1. **Settings → Devices & Services → Add Integration**
2. Vyhledej "Rohlik Voice"
3. Zadej:
   - E-mail (Rohlik.cz)
   - Heslo (Rohlik.cz)  
   - OpenAI API klíč
4. Údaje se uloží **šifrovaně**

### Krok 4: Přidej Lovelace kartu

1. Přidej resource (jednou):
   - **Settings → Dashboards → Resources → Add**
   - URL: `/local/rohlik-voice-card.js`
   - Typ: JavaScript Module

2. Přidej kartu do dashboardu:

```yaml
type: custom:rohlik-voice-card
show_cart: true
show_transcript: true
```

## Použití

1. Na tabletu otevři Home Assistant dashboard
2. Klikni a drž tlačítko mikrofonu
3. Řekni co chceš (např. "Přidej mléko do košíku")
4. Pusť tlačítko
5. Počkej na hlasovou odpověď

### Příklady příkazů

- "Přidej do košíku mléko"
- "Jaké mají jogurty?"
- "Co mám v košíku?"
- "Odeber rohlíky z košíku"
- "Najdi bezlepkový chléb"

### Příklad konverzace

```
Ty: "Přidej mléko do košíku"

Asistent: "Našel jsem 15 druhů mléka. Chcete plnotučné, 
           polotučné nebo odstředěné?"

Ty: "Polotučné Tatra"

Asistent: "Přidal jsem Tatra mléko polotučné 1l za 24.90 Kč 
           do košíku. Máte tam teď 3 položky za 89 Kč."
```

## Bezpečnost

- **Šifrované ukládání** - Credentials jsou uloženy šifrovaně v Home Assistant
- **Žádné plain-text soubory** - Hesla se nikde neukládají v čitelné podobě
- **Lokální zpracování** - Audio jde přímo do OpenAI, ne přes třetí strany
- **HTTPS** - Veškerá komunikace je šifrovaná

## Řešení problémů

### "Nelze se připojit k Rohlíku"

- Zkontroluj přihlašovací údaje
- Ověř, že účet funguje na rohlik.cz

### "Neplatný OpenAI API klíč"

- Klíč musí začínat `sk-`
- Ověř, že máš přístup k Realtime API

### Mikrofon nefunguje

- Povol přístup k mikrofonu v prohlížeči
- Zkontroluj, že používáš HTTPS (nebo localhost)

### Žádná odpověď

- Zkontroluj konzoli prohlížeče (F12)
- Ověř, že Home Assistant běží

## Manuální instalace (alternativa)

Pokud nechceš HACS:

1. Stáhni ZIP z GitHubu
2. Rozbal do `config/custom_components/rohlik_voice/`
3. Zkopíruj `www/rohlik-voice-card.js` do `config/www/`
4. Restartuj Home Assistant

## Struktura projektu

```
rohlik-ha-integration/
├── custom_components/
│   └── rohlik_voice/
│       ├── __init__.py          # HA integration setup
│       ├── manifest.json        # HA metadata
│       ├── config_flow.py       # UI konfigurace
│       ├── realtime_api.py      # OpenAI Realtime API
│       ├── mcp_client.py        # Rohlik MCP klient
│       ├── tools.py             # AI tools definice
│       ├── websocket_api.py     # WebSocket endpoint
│       ├── const.py             # Konstanty
│       ├── strings.json         # UI texty
│       └── translations/        # Překlady
├── www/
│   └── rohlik-voice-card.js     # Lovelace karta
├── hacs.json                    # HACS metadata
└── README.md
```

## Licence

MIT

## Poděkování

- [Rohlik MCP Server](https://www.rohlik.cz/stranka/mcp-server) - Oficiální MCP server
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) - Audio AI
- [Home Assistant](https://www.home-assistant.io/) - Smart home platforma
