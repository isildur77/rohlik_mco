"""Rohlik tools definitions for OpenAI function calling."""

from typing import Any

# Tool definitions for OpenAI Realtime API
ROHLIK_TOOLS = [
    {
        "type": "function",
        "name": "search_products",
        "description": "Vyhledá produkty na Rohlíku podle názvu nebo popisu. Použij když uživatel chce najít nebo přidat konkrétní produkt.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Hledaný výraz (název produktu, značka, kategorie)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximální počet výsledků (výchozí 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "add_to_cart",
        "description": "Přidá produkt do košíku. Potřebuje ID produktu z vyhledávání.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID produktu z vyhledávání",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Počet kusů (výchozí 1)",
                    "default": 1,
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "type": "function",
        "name": "get_cart",
        "description": "Zobrazí aktuální obsah košíku včetně produktů a celkové ceny.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "remove_from_cart",
        "description": "Odebere produkt z košíku.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID produktu k odebrání",
                },
            },
            "required": ["product_id"],
        },
    },
]

# System prompt for the voice assistant
SYSTEM_PROMPT = """Jsi hlasový asistent pro nakupování na Rohlík.cz. Pomáháš uživateli s nákupem potravin.

PRAVIDLA:
1. Mluv česky, přátelsky a stručně
2. Když uživatel chce přidat produkt, nejdřív ho vyhledej pomocí search_products
3. Pokud je více výsledků, zeptej se uživatele který chce (značka, velikost, cena)
4. Po přidání do košíku potvrď co jsi přidal a řekni aktuální stav košíku
5. Ceny uvádej v Kč
6. Když si nejsi jistý, zeptej se

PŘÍKLADY ODPOVĚDÍ:
- "Našel jsem 5 druhů mléka. Chcete polotučné, plnotučné nebo odstředěné?"
- "Přidal jsem Tatra mléko 1l za 24.90 Kč. V košíku máte 3 položky za 89 Kč celkem."
- "Omlouvám se, tento produkt jsem nenašel. Můžete to zkusit popsat jinak?"
"""


def format_search_results(results: dict[str, Any]) -> str:
    """Format search results for voice response."""
    if "error" in results:
        return f"Při vyhledávání došlo k chybě: {results['error']}"
    
    content = results.get("content", [])
    if not content:
        return "Nenašel jsem žádné produkty odpovídající vašemu dotazu."
    
    # Parse the content - MCP returns text content
    if isinstance(content, list) and len(content) > 0:
        text_content = content[0].get("text", "")
        return text_content
    
    return "Výsledky vyhledávání jsou k dispozici."


def format_cart_contents(cart: dict[str, Any]) -> str:
    """Format cart contents for voice response."""
    if "error" in cart:
        return f"Nepodařilo se načíst košík: {cart['error']}"
    
    content = cart.get("content", [])
    if not content:
        return "Košík je prázdný."
    
    if isinstance(content, list) and len(content) > 0:
        text_content = content[0].get("text", "")
        return text_content
    
    return "Obsah košíku je k dispozici."


def format_add_result(result: dict[str, Any]) -> str:
    """Format add to cart result for voice response."""
    if "error" in result:
        return f"Nepodařilo se přidat do košíku: {result['error']}"
    
    content = result.get("content", [])
    if isinstance(content, list) and len(content) > 0:
        text_content = content[0].get("text", "")
        return text_content
    
    return "Produkt byl přidán do košíku."


def format_remove_result(result: dict[str, Any]) -> str:
    """Format remove from cart result for voice response."""
    if "error" in result:
        return f"Nepodařilo se odebrat z košíku: {result['error']}"
    
    content = result.get("content", [])
    if isinstance(content, list) and len(content) > 0:
        text_content = content[0].get("text", "")
        return text_content
    
    return "Produkt byl odebrán z košíku."
