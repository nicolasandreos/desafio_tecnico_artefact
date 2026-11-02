"""Index the store policy PDF and expose it as one Agno knowledge base."""

from __future__ import annotations

import hashlib
from pathlib import Path

from agno.knowledge.chunking.semantic import SemanticChunking
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.pdf_reader import PDFReader
from agno.vectordb.chroma import ChromaDb
from agno.vectordb.search import SearchType

from emporio_agent.config import load_settings
from emporio_agent.logging import log_failure

POLICY_SOURCE = "políticas_da_loja.pdf"
_COLLECTION = "store_policies"
_EMBEDDING_MODEL = "text-embedding-3-small"
_MARK = "index_complete"
_MAX_RESULTS = 3


def ensure_policy_index() -> Knowledge:
    """Return the policy knowledge base, indexing the PDF when the mark differs.

    Raises:
        FileNotFoundError: The PDF is absent. The message is the file name.
    """
    pdf_path = Path(load_settings().data_dir) / POLICY_SOURCE
    if not pdf_path.is_file():
        log_failure("missing_file", file_name=POLICY_SOURCE)
        raise FileNotFoundError(POLICY_SOURCE)
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    knowledge = _policy_knowledge()
    vector_db = knowledge.vector_db
    if isinstance(vector_db, ChromaDb) and _is_complete(vector_db, digest):
        return knowledge
    if isinstance(vector_db, ChromaDb) and vector_db.exists():
        vector_db.drop()
    try:
        _index(knowledge, pdf_path)
        if not isinstance(vector_db, ChromaDb) or vector_db.get_count() <= 0:
            raise RuntimeError("Policy index produced no chunks")
        _mark_complete(vector_db, digest)
    except Exception:
        log_failure("index_failed", file_name=POLICY_SOURCE)
        if isinstance(vector_db, ChromaDb):
            vector_db.drop()
        raise
    return knowledge


def _policy_knowledge() -> Knowledge:
    """Return the persistent policy collection and its semantic reader."""
    embedder = OpenAIEmbedder(id=_EMBEDDING_MODEL)
    settings = load_settings()
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    vector_db = ChromaDb(
        collection=_COLLECTION,
        path=str(settings.chroma_path),
        persistent_client=True,
        embedder=embedder,
        search_type=SearchType.vector,
    )
    return Knowledge(vector_db=vector_db, max_results=_MAX_RESULTS)


def _index(knowledge: Knowledge, pdf_path: Path) -> None:
    """Insert semantic chunks of the PDF. Products and orders are not embedded."""
    embedder = knowledge.vector_db.embedder
    reader = PDFReader(
        split_on_pages=False,
        chunking_strategy=SemanticChunking(embedder=embedder),
    )
    knowledge.insert(
        name=POLICY_SOURCE,
        path=str(pdf_path),
        reader=reader,
        metadata={"source": POLICY_SOURCE},
    )


def _is_complete(vector_db: ChromaDb, digest: str) -> bool:
    """Return True when the collection mark equals the current PDF hash."""
    if not vector_db.exists():
        return False
    metadata = _collection(vector_db).metadata or {}
    return metadata.get(_MARK) == digest


def _mark_complete(vector_db: ChromaDb, digest: str) -> None:
    """Record the PDF hash only after chunks are stored."""
    _collection(vector_db).modify(metadata={_MARK: digest})


def _collection(vector_db: ChromaDb):
    """Return the Chroma collection for the policy index."""
    return vector_db.client.get_collection(name=vector_db.collection_name)
