"""RAGFlow client for document ingestion and retrieval (Forge-Stream Phase 1).

Supports both ragflow-sdk (Python >=3.12) and HTTP API fallback for compatibility.
"""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings


class RAGFlowClient:
    """Thin wrapper over RAGFlow for dataset creation, upload, parse polling, and search."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.ragflow_api_url).rstrip("/")
        self.api_key = api_key or settings.ragflow_api_key
        self._dataset_id: Optional[str] = None
        self._client: Any = None  # ragflow_sdk RAGFlow instance if available

        if self.api_key:
            try:
                from ragflow_sdk import RAGFlow

                self._client = RAGFlow(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                self._client = None

    def is_available(self) -> bool:
        """Return True if API key is set and (if using SDK) connection works."""
        if not self.api_key:
            return False
        if self._client is not None:
            try:
                self._client.list_datasets(page=1, page_size=1)
                return True
            except Exception:
                return False
        # HTTP fallback: we only check key presence
        return True

    def ensure_dataset(self, name: Optional[str] = None, unique: bool = True) -> str:
        """Get or create the workspace dataset; return its ID.

        If unique is True (default), appends a short random suffix to the default
        dataset name and always creates (no list reuse) so we own the dataset.
        """
        base = name or settings.ragflow_dataset_name
        use_unique_name = unique and base == settings.ragflow_dataset_name
        if use_unique_name:
            name = f"{base}-{secrets.token_hex(4)}"
        else:
            name = base
        if self._client is not None:
            return self._ensure_dataset_sdk(name, create_only=use_unique_name)
        return self._ensure_dataset_http(name, create_only=use_unique_name)

    def _ensure_dataset_sdk(self, name: str, create_only: bool = False) -> str:
        if not create_only:
            datasets = self._client.list_datasets(name=name)
            if datasets:
                self._dataset_id = datasets[0].id
                return self._dataset_id
        dataset = self._client.create_dataset(
            name=name, embedding_model=settings.ragflow_embedding_model
        )
        self._dataset_id = dataset.id
        return self._dataset_id

    def _ensure_dataset_http(self, name: str, create_only: bool = False) -> str:
        import requests

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        if not create_only:
            r = requests.get(
                f"{self.base_url}/api/v1/datasets",
                headers=headers,
                params={"name": name, "page": 1, "page_size": 10},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 0:
                raise RuntimeError(data.get("message", "list datasets failed"))
            raw = data.get("data")
            items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
            for item in items:
                if not isinstance(item, dict):
                    continue
                if (item.get("name") or "").lower() == name.lower():
                    self._dataset_id = item.get("id") or item.get("_id")
                    if self._dataset_id:
                        return self._dataset_id

        # Create (explicit permission so we own it)
        r = requests.post(
            f"{self.base_url}/api/v1/datasets",
            headers=headers,
            json={
                "name": name,
                "permission": "me",
                "embedding_model": settings.ragflow_embedding_model,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "create dataset failed"))
        payload = data.get("data")
        if isinstance(payload, dict):
            self._dataset_id = payload.get("id") or payload.get("_id")
        elif isinstance(payload, str):
            self._dataset_id = payload
        else:
            self._dataset_id = None
        if not self._dataset_id:
            raise RuntimeError("create dataset response missing dataset id")
        return self._dataset_id

    def upload_document(
        self,
        dataset_id: Optional[str] = None,
        file_path: Optional[Path | str] = None,
        content: Optional[bytes] = None,
        display_name: Optional[str] = None,
    ) -> str:
        """Upload a single document; trigger parsing (DDU). Return document ID."""
        did = dataset_id or self.ensure_dataset()
        if file_path is not None:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(str(path))
            blob = path.read_bytes()
            display_name = display_name or path.name
        elif content is not None:
            blob = content
            display_name = display_name or "upload.txt"
        else:
            raise ValueError("Provide file_path or content")

        if self._client is not None:
            return self._upload_document_sdk(did, display_name, blob)
        return self._upload_document_http(did, display_name, blob)

    def _upload_document_sdk(self, dataset_id: str, display_name: str, blob: bytes) -> str:
        datasets = self._client.list_datasets(id=dataset_id)
        if not datasets:
            raise ValueError(f"Dataset not found: {dataset_id}")
        dataset = datasets[0]
        dataset.upload_documents([{"display_name": display_name, "blob": blob}])
        docs = dataset.list_documents()
        if not docs:
            raise RuntimeError("upload_documents returned but list_documents is empty")
        doc_id = docs[0].id
        dataset.async_parse_documents([doc_id])
        return doc_id

    def _upload_document_http(self, dataset_id: str, display_name: str, blob: bytes) -> str:
        import requests

        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"file": (display_name, blob)}
        r = requests.post(
            f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
            headers=headers,
            files=files,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "upload failed"))
        payload = data.get("data")
        if isinstance(payload, list) and payload:
            first = payload[0]
            doc_id = first.get("id") if isinstance(first, dict) else None
        elif isinstance(payload, dict):
            doc_id = payload.get("id")
        else:
            doc_id = None
        if not doc_id:
            raise RuntimeError("upload response missing document id")
        # Trigger parse (if endpoint exists)
        try:
            parse_r = requests.post(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks",
                headers={**headers, "Content-Type": "application/json"},
                json={"document_ids": [doc_id]},
                timeout=30,
            )
            if parse_r.status_code == 200 and parse_r.json().get("code") == 0:
                pass  # parse triggered
        except Exception:
            pass  # optional
        return doc_id

    def get_parsing_status(
        self,
        dataset_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return parsing status for a document (or all in dataset)."""
        did = dataset_id or self._dataset_id or self.ensure_dataset()
        if self._client is not None:
            return self._get_parsing_status_sdk(did, document_id)
        return self._get_parsing_status_http(did, document_id)

    def _get_parsing_status_sdk(
        self, dataset_id: str, document_id: Optional[str]
    ) -> Dict[str, Any]:
        datasets = self._client.list_datasets(id=dataset_id)
        if not datasets:
            return {"documents": [], "message": "dataset not found"}
        dataset = datasets[0]
        docs = dataset.list_documents(id=document_id) if document_id else dataset.list_documents()
        documents = [
            {
                "id": d.id,
                "name": getattr(d, "name", "") or getattr(d, "display_name", ""),
                "run": getattr(d, "run", "UNSTART"),
                "progress": getattr(d, "progress", 0),
                "chunk_count": getattr(d, "chunk_count", 0),
            }
            for d in docs
        ]
        return {"documents": documents}

    def _get_parsing_status_http(
        self, dataset_id: str, document_id: Optional[str]
    ) -> Dict[str, Any]:
        import requests

        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"page": 1, "page_size": 100}
        if document_id:
            params["id"] = document_id
        r = requests.get(
            f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
            headers=headers,
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            return {"documents": [], "message": data.get("message", "list documents failed")}
        payload = data.get("data")
        if isinstance(payload, dict) and "docs" in payload:
            items = payload["docs"] or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        documents = [
            {
                "id": d.get("id", ""),
                "name": d.get("name") or d.get("display_name", ""),
                "run": d.get("run", "UNSTART"),
                "progress": d.get("progress", 0),
                "chunk_count": d.get("chunk_count", 0),
            }
            for d in items
            if isinstance(d, dict)
        ]
        return {"documents": documents}

    def wait_for_parsed(
        self,
        dataset_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        timeout_sec: Optional[float] = None,
        poll_interval_sec: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Poll until the given documents are parsed (DONE or FAIL) or timeout."""
        did = dataset_id or self._dataset_id or self.ensure_dataset()
        timeout_sec = timeout_sec or settings.ragflow_parse_timeout_sec
        poll_interval_sec = poll_interval_sec or settings.ragflow_parse_poll_interval_sec
        deadline = time.monotonic() + timeout_sec
        if self._client is not None and document_ids:
            try:
                result = self._client.list_datasets(id=did)
                if not result:
                    return []
                dataset = result[0]
                # parse_documents blocks until done
                finished = dataset.parse_documents(
                    document_ids,
                )
                return [
                    {"id": doc_id, "status": status, "chunk_count": cc, "token_count": tc}
                    for doc_id, status, cc, tc in finished
                ]
            except Exception:
                pass  # fall through to polling
        # Poll by status
        seen_ids = set(document_ids or [])
        while time.monotonic() < deadline:
            status = self.get_parsing_status(did, None)
            docs = status.get("documents", [])
            if document_ids:
                docs = [d for d in docs if d["id"] in seen_ids]
            done = all(d.get("run") in ("DONE", "FAIL", "CANCEL") for d in docs)
            if done and docs:
                return docs
            time.sleep(poll_interval_sec)
        return status.get("documents", [])

    def search(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Return top-k chunks for the query from the dataset."""
        did = dataset_id or self._dataset_id or self.ensure_dataset()
        if self._client is not None:
            return self._search_sdk(did, query, top_k, similarity_threshold)
        return self._search_http(did, query, top_k, similarity_threshold)

    def _search_sdk(
        self,
        dataset_id: str,
        query: str,
        top_k: int,
        similarity_threshold: Optional[float],
    ) -> List[Dict[str, Any]]:
        # SDK retrieval: use retrieval API if available, else list chunks and filter
        datasets = self._client.list_datasets(id=dataset_id)
        if not datasets:
            return []
        dataset = datasets[0]
        # RAGFlow Python API: retrieval might be under dataset.retrieve or similar
        if hasattr(dataset, "retrieve"):
            result = dataset.retrieve(query=query, top_k=top_k)
            return [{"content": c.content if hasattr(c, "content") else str(c), "similarity": getattr(c, "similarity", None)} for c in (result or [])]
        # Fallback: list chunks (no semantic search without retrieval endpoint)
        chunks: List[Dict[str, Any]] = []
        for doc in dataset.list_documents():
            for chunk in doc.list_chunks(page_size=top_k):
                content = getattr(chunk, "content", None) or str(chunk)
                chunks.append({"content": content, "similarity": None})
                if len(chunks) >= top_k:
                    return chunks
        return chunks

    def _search_http(
        self,
        dataset_id: str,
        query: str,
        top_k: int,
        similarity_threshold: Optional[float],
    ) -> List[Dict[str, Any]]:
        import requests

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "dataset_ids": [dataset_id],
            "question": query.strip(),
            "top_k": top_k,
        }
        if similarity_threshold is not None:
            body["similarity_threshold"] = similarity_threshold
        r = requests.post(
            f"{self.base_url}/api/v1/retrieval",
            headers=headers,
            json=body,
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  [RAGFlow] search HTTP {r.status_code}: {r.text[:200]}")
            return []
        data = r.json()
        if data.get("code") != 0:
            print(f"  [RAGFlow] search error code {data.get('code')}: {data.get('message', '')}")
            return []
        payload = data.get("data")
        chunks = payload.get("chunks", []) if isinstance(payload, dict) else []
        if not isinstance(chunks, list):
            chunks = []
        return [
            {
                "content": c.get("content", c.get("text", "")),
                "similarity": c.get("similarity"),
            }
            for c in chunks[:top_k]
            if isinstance(c, dict)
        ]
