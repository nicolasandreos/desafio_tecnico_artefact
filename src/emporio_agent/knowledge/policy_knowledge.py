"""Index and search the store policy PDF with semantic chunks."""

from __future__ import annotations

from pathlib import Path

from emporio_agent.config import load_settings
from emporio_agent.logging import log_failure

POLICY_SOURCE = "políticas_da_loja.pdf"
_COLLECTION = "store_policies"
_EMBEDDING_MODEL = "text-embedding-3-small"
_MAX_DISTANCE = 0.55


def rebuild_policy_index(pdf_path: Path) -> None:
    """Replace the store_policies collection with semantic chunks of the PDF.

    Raises:
        FileNotFoundError: The PDF is absent. The message is the file name.
    """
    path = Path(pdf_path)
    if not path.is_file():
        log_failure("missing_file", file_name=path.name)
        raise FileNotFoundError(path.name)
    _write_index(path)


def search_passages(question: str) -> list[dict[str, object]]:
    """Return relevant policy passages. A missing index raises FileNotFoundError."""
    knowledge = _knowledge()
    if not knowledge.vector_db.exists():
        raise FileNotFoundError(_COLLECTION)
    documents = knowledge.search(question, max_results=4)
    passages: list[dict[str, object]] = []
    for document in documents:
        distance = document.meta_data.get("similarity_score")
        if isinstance(distance, (int, float)) and not isinstance(distance, bool):
            if float(distance) > _MAX_DISTANCE:
                continue
        text = document.content.strip()
        if text == "":
            continue
        source = document.meta_data.get("source") or POLICY_SOURCE
        passages.append({"text": text, "source": str(source)})
    return passages


def _write_index(path: Path) -> None:
    """Chunk the PDF semantically and store the embeddings in Chroma."""
    from agno.knowledge.chunking.semantic import SemanticChunking
    from agno.knowledge.embedder.openai import OpenAIEmbedder
    from agno.knowledge.knowledge import Knowledge
    from agno.knowledge.reader.pdf_reader import PDFReader

    embedder = OpenAIEmbedder(id=_EMBEDDING_MODEL)
    vector_db = _chroma(embedder)
    if vector_db.exists():
        vector_db.drop()
    knowledge = Knowledge(vector_db=vector_db)
    reader = PDFReader(
        split_on_pages=False,
        chunking_strategy=SemanticChunking(embedder=embedder),
    )
    knowledge.insert(
        name=POLICY_SOURCE,
        path=str(path),
        reader=reader,
        metadata={"source": POLICY_SOURCE},
    )


def _knowledge() -> object:
    """Return the policy knowledge base without rebuilding it."""
    from agno.knowledge.embedder.openai import OpenAIEmbedder
    from agno.knowledge.knowledge import Knowledge

    return Knowledge(vector_db=_chroma(OpenAIEmbedder(id=_EMBEDDING_MODEL)))


def _chroma(embedder: object) -> object:
    """Return the persistent store_policies collection."""
    from agno.vectordb.chroma import ChromaDb

    settings = load_settings()
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return ChromaDb(
        collection=_COLLECTION,
        path=str(settings.chroma_path),
        persistent_client=True,
        embedder=embedder,
    )
