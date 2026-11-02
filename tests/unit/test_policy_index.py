"""The policy collection is valid only when its completion mark matches the PDF."""

import hashlib
from pathlib import Path

import pytest
from chromadb import PersistentClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from emporio_agent.knowledge.policy_knowledge import ensure_policy_index

_SOURCE = "políticas_da_loja.pdf"
_COLLECTION = "store_policies"
_SENTINEL = "OLD_POLICY_SENTINEL"
_TEXT = "A devolucao pode ser feita em sete dias corridos apos a compra do instrumento."


def _pdf(folder: Path) -> Path:
    """Write one page whose extracted text is the policy sentence."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({_TEXT}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    path = folder / _SOURCE
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _digest(path: Path) -> str:
    """Return the SHA-256 hex digest of the PDF bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Point settings at empty data and chroma folders."""
    data = tmp_path / "data"
    chroma = tmp_path / "chroma"
    data.mkdir()
    chroma.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("CHROMA_PATH", str(chroma))
    return data, chroma


def _names(chroma: Path) -> list[str]:
    """Return collection names in a fresh client."""
    client = PersistentClient(path=str(chroma))
    return [collection.name for collection in client.list_collections()]


def _documents(chroma: Path) -> list[str]:
    """Return stored document text for the policy collection."""
    collection = PersistentClient(path=str(chroma)).get_collection(_COLLECTION)
    return list(collection.get()["documents"] or [])


def _patch_embedder(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace network embeddings with a fixed vector and record each call."""
    calls: list[str] = []
    vector = [0.1] * 1536

    def get_embedding(self: object, text: str) -> list[float]:
        calls.append(text)
        return vector

    def get_embedding_and_usage(
        self: object, text: str
    ) -> tuple[list[float], None]:
        calls.append(text)
        return vector, None

    monkeypatch.setattr(
        "agno.knowledge.embedder.openai.OpenAIEmbedder.get_embedding",
        get_embedding,
    )
    monkeypatch.setattr(
        "agno.knowledge.embedder.openai.OpenAIEmbedder.get_embedding_and_usage",
        get_embedding_and_usage,
    )
    return calls


def test_missing_pdf_raises_and_creates_no_collection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing PDF names the file and does not create the policy collection."""
    _data, chroma = _paths(tmp_path, monkeypatch)

    with pytest.raises(FileNotFoundError, match=_SOURCE):
        ensure_policy_index()

    assert _COLLECTION not in _names(chroma)


def test_matching_mark_does_not_call_the_embedder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completion mark equal to the file hash skips embedding."""
    data, chroma = _paths(tmp_path, monkeypatch)
    digest = _digest(_pdf(data))
    client = PersistentClient(path=str(chroma))
    collection = client.create_collection(
        _COLLECTION, metadata={"index_complete": digest}
    )
    collection.add(
        ids=["current"],
        documents=["current policy"],
        embeddings=[[0.2] * 8],
    )
    calls = _patch_embedder(monkeypatch)

    knowledge = ensure_policy_index()

    assert calls == []
    assert knowledge.max_results == 3
    assert "current policy" in _documents(chroma)


def test_different_hash_drops_the_collection_and_indexes_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A different completion mark drops the old collection and indexes the PDF."""
    data, chroma = _paths(tmp_path, monkeypatch)
    _pdf(data)
    client = PersistentClient(path=str(chroma))
    collection = client.create_collection(
        _COLLECTION, metadata={"index_complete": "0" * 64}
    )
    collection.add(ids=["old"], documents=[_SENTINEL], embeddings=[[0.2] * 8])
    calls = _patch_embedder(monkeypatch)

    ensure_policy_index()

    assert calls
    documents = _documents(chroma)
    assert _SENTINEL not in documents
    assert any(_TEXT in document for document in documents)
    marked = PersistentClient(path=str(chroma)).get_collection(_COLLECTION)
    assert marked.metadata is not None
    assert marked.metadata["index_complete"] == _digest(data / _SOURCE)


def test_chunks_without_a_completion_mark_are_not_the_current_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chunks with no completion mark are dropped and are not served."""
    data, chroma = _paths(tmp_path, monkeypatch)
    _pdf(data)
    client = PersistentClient(path=str(chroma))
    collection = client.create_collection(_COLLECTION)
    collection.add(ids=["old"], documents=[_SENTINEL], embeddings=[[0.2] * 8])
    _patch_embedder(monkeypatch)

    knowledge = ensure_policy_index()
    found = knowledge.search(_SENTINEL)

    assert _SENTINEL not in _documents(chroma)
    assert all(_SENTINEL not in (document.content or "") for document in found)


def test_failed_rebuild_does_not_leave_the_old_collection_searchable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed insert after the drop removes the previous collection."""
    data, chroma = _paths(tmp_path, monkeypatch)
    _pdf(data)
    client = PersistentClient(path=str(chroma))
    collection = client.create_collection(_COLLECTION)
    collection.add(ids=["old"], documents=[_SENTINEL], embeddings=[[0.2] * 8])

    def fail(self: object, *args: object, **kwargs: object) -> None:
        raise RuntimeError("insert failed")

    monkeypatch.setattr("agno.knowledge.knowledge.Knowledge.insert", fail)

    with pytest.raises(RuntimeError, match="insert failed"):
        ensure_policy_index()

    assert _COLLECTION not in _names(chroma)
