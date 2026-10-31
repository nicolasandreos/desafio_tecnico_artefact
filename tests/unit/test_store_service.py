"""Store profile answers stay inside the supplied text."""

from pathlib import Path

from emporio_agent.services.store_service import get_store_context

_ROOT = Path(__file__).resolve().parents[2]
_PROFILE = _ROOT / "data" / "store_profile.md"

_FORBIDDEN = (
    "telefone",
    "phone",
    "horário",
    "horario",
    "rua ",
    "avenida",
    "abre às",
    "funcionamento",
    "(",
)


def test_facts_are_only_the_supplied_profile_text(tmp_path: Path) -> None:
    """A supplied profile is returned in full and nothing is added to it."""
    profile = tmp_path / "store_profile.md"
    profile.write_text("Emporio da Musica fica em Campo Grande.\n", encoding="utf-8")

    result = get_store_context(profile)

    assert result["facts"] == "Emporio da Musica fica em Campo Grande.\n"
    assert "error" not in result
    for token in ("telefone", "phone", "horário", "rua "):
        assert token not in result["facts"].lower()


def test_missing_profile_is_unavailable(tmp_path: Path) -> None:
    """No supplied profile returns unavailable and no invented facts."""
    result = get_store_context(tmp_path / "missing.md")

    assert result == {"error": "unavailable"}
    assert "facts" not in result


def test_shipped_profile_states_only_supported_store_facts() -> None:
    """The shipped profile names the store and omits hours, street, and phone."""
    text = _PROFILE.read_text(encoding="utf-8")
    folded = text.lower()

    assert "Emporio da Musica" in text
    assert "Campo Grande" in text
    assert "Mato Grosso do Sul" in text
    assert "instrumentos musicais" in folded
    for token in _FORBIDDEN:
        assert token not in folded

    result = get_store_context(_PROFILE)
    assert result["facts"] == text
