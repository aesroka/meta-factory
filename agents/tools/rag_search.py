"""RAG search tool for agents to query RAGFlow datasets with similarity thresholds."""

from typing import Any, Dict, List, Optional

from config import settings


def rag_search(
    query: str,
    dataset_id: Optional[str] = None,
    top_k: int = 5,
    similarity_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Query a RAGFlow dataset and return top-k chunks with optional similarity threshold.

    Agents should use this to retrieve relevant passages from the workspace dataset
    (transcripts, code, docs) instead of reading raw files.

    Args:
        query: Natural language or keyword search query.
        dataset_id: RAGFlow dataset ID. If None, uses the default workspace dataset.
        top_k: Maximum number of chunks to return (default 5).
        similarity_threshold: Optional minimum similarity score (0–1) to filter results.

    Returns:
        List of dicts with "content" and optionally "similarity". Empty if RAGFlow
        is not configured or the search fails.
    """
    if not settings.ragflow_api_key:
        return []

    from librarian.rag_client import RAGFlowClient

    client = RAGFlowClient()
    if not client.is_available():
        return []

    try:
        chunks = client.search(
            query=query,
            dataset_id=dataset_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        if similarity_threshold is not None and chunks:
            chunks = [c for c in chunks if (c.get("similarity") or 0) >= similarity_threshold]
        return chunks[:top_k]
    except Exception:
        return []
