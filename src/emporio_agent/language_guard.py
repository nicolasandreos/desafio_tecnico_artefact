"""Refuse a message whose own wording is not Portuguese."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

_TOKEN = re.compile(r"[0-9A-Za-zÀ-ÿ]+")

_PORTUGUESE = frozenset(
    {
        "o",
        "os",
        "um",
        "uma",
        "de",
        "do",
        "da",
        "dos",
        "das",
        "em",
        "na",
        "nas",
        "nos",
        "que",
        "qual",
        "quais",
        "como",
        "onde",
        "quando",
        "quanto",
        "por",
        "para",
        "pra",
        "com",
        "sem",
        "meu",
        "minha",
        "pedido",
        "pedidos",
        "preco",
        "loja",
        "lojas",
        "politica",
        "horario",
        "estoque",
        "promocao",
        "produto",
        "produtos",
        "instrumento",
        "instrumentos",
        "musica",
        "musical",
        "musicais",
        "cancelado",
        "cancelada",
        "esta",
        "tem",
        "quero",
        "pode",
        "devolucao",
        "instrucoes",
        "instrucao",
        "catalogo",
        "pagamento",
        "disponivel",
        "custa",
        "fica",
        "abre",
        "obrigado",
        "voce",
        "passa",
        "receita",
        "bolo",
        "lado",
        "mostra",
        "suas",
        "regras",
        "regra",
        "lista",
        "inteiro",
        "inteira",
        "altera",
        "cancela",
        "faz",
        "pagar",
        "nao",
        "sim",
        "favor",
        "especifica",
        "especifico",
    }
)

_ENGLISH = frozenset(
    {
        "the",
        "what",
        "where",
        "when",
        "how",
        "why",
        "which",
        "is",
        "are",
        "was",
        "were",
        "does",
        "did",
        "can",
        "could",
        "would",
        "should",
        "please",
        "store",
        "hours",
        "price",
        "order",
        "cancel",
        "recipe",
        "show",
        "your",
        "instructions",
        "ignore",
        "rules",
        "catalog",
        "catalogue",
        "payment",
        "return",
        "my",
        "of",
        "to",
        "for",
        "and",
        "or",
        "in",
        "on",
        "at",
        "this",
        "that",
        "with",
        "from",
        "about",
        "have",
        "has",
        "want",
        "need",
        "tell",
        "give",
        "list",
        "entire",
        "whole",
        "hello",
        "hi",
        "hey",
        "thanks",
    }
)

LANGUAGE_REFUSAL = (
    "Eu me comunico apenas em português e não respondo a esse pedido. "
    "Escreva em português para que eu possa ajudar."
)


def screen_language(
    message: str, tools: Mapping[str, object] | None = None
) -> dict[str, str | None]:
    """Refuse non-Portuguese wording. Tool callables are not invoked."""
    del tools
    if _is_portuguese_request(message):
        return {"kind": "allow", "reason": "allow", "reply": None}
    return {"kind": "cannot-help", "reason": "language", "reply": LANGUAGE_REFUSAL}


def _is_portuguese_request(message: str) -> bool:
    """Return True when the message is Portuguese or shows no language."""
    portuguese = 0
    english = 0
    for token in _TOKEN.findall(message):
        folded = _fold(token)
        if folded in _PORTUGUESE or _has_accent(token):
            portuguese += 1
        if folded in _ENGLISH:
            english += 1
    if english > 0 and portuguese == 0:
        return False
    return True


def _fold(token: str) -> str:
    """Return a lower-case token without accents."""
    normalized = unicodedata.normalize("NFKD", token)
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_marks.casefold()


def _has_accent(token: str) -> bool:
    """Return True when the token uses a Portuguese diacritic."""
    return any(
        unicodedata.combining(char) for char in unicodedata.normalize("NFKD", token)
    ) or any(char in "ãõçáéíóúâêôà" for char in token.casefold())
