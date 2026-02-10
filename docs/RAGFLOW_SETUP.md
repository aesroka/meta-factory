# RAGFlow setup and end-to-end demo

This guide gets you from zero to a working RAGFlow instance wired into meta-factory, with dummy data and a single script so you can see the full flow.

---

## 1. Run RAGFlow with Docker

**Prerequisites:** Docker and Docker Compose (Docker ≥24, Compose ≥2.26). On Mac, Docker Desktop is enough.

### 1.1 (Linux only) Set `vm.max_map_count`

RAGFlow uses Elasticsearch, which needs this:

```bash
sudo sysctl -w vm.max_map_count=262144
```

On **macOS** you can skip this (or run the one-off container below if you hit ES issues):

```bash
docker run --rm --privileged --pid=host alpine sysctl -w vm.max_map_count=262144
```

### 1.2 Clone and start RAGFlow

```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/docker
docker compose up -d
```

First run can take a few minutes (pulling images, starting Elasticsearch, MySQL, MinIO, Redis, etc.).

### 1.3 Check it’s up

- **Web UI:** open **http://127.0.0.1** (or http://localhost). You should see the RAGFlow login.
- **API:** RAGFlow’s HTTP API is on port **9380**. Our app uses `http://localhost:9380` by default.

If the UI is on a different port, check `ragflow/docker/docker-compose.yml` for the frontend port; the **backend API** should still be 9380 unless you changed it.

### 1.4 Create an account and get an API key

1. In the RAGFlow UI, sign up / log in.
2. Click your **avatar** (top right) → **API**.
3. Copy your **API key** (or create one). You’ll put this in meta-factory’s `.env`.

---

## 2. Configure meta-factory

In the **meta-factory** repo root:

### 2.1 Set RAGFlow in `.env`

Create or edit `.env` and set:

```bash
# RAGFlow (use the key from RAGFlow UI → Avatar → API)
META_FACTORY_RAGFLOW_API_URL=http://localhost:9380
META_FACTORY_RAGFLOW_API_KEY=your-ragflow-api-key-here
# Optional: dataset name used by sync_workspace (default: meta-factory-workspace)
# META_FACTORY_RAGFLOW_DATASET_NAME=meta-factory-workspace
```

Use your real API key from step 1.4. If RAGFlow runs on another host/port, change `META_FACTORY_RAGFLOW_API_URL` accordingly.

### 2.2 Put some files in `workspace/`

Everything we sync and search comes from the **workspace** directory.

**Option A – Use the included dummy files**

We’ve added two small samples under `workspace/`:

- `workspace/sample_transcript.txt` – short “discovery call” snippet  
- `workspace/sample_notes.txt` – short “technical notes” snippet  

Leave them there and the demo script will use them.

**Option B – Use your own or demo content**

Copy in any text you like (e.g. from `demo/greenfield/`):

```bash
cp demo/greenfield/discovery_call_transcript.txt workspace/
# optional: add more .txt / .md / .py etc.
```

Supported extensions are listed in `librarian/librarian.py` (`WORKSPACE_SYNC_EXTENSIONS`).

---

## 3. Run the end-to-end demo

From the **meta-factory** repo root, with your venv activated:

```bash
source venv/bin/activate   # or: . venv/bin/activate
python scripts/rag_demo.py
```

The script will:

1. **Sync** – Scan `workspace/`, create the RAGFlow dataset (e.g. `meta-factory-workspace`), upload all supported files, and trigger parsing (DDU).
2. **Wait** – Poll until RAGFlow has finished parsing (or timeout).
3. **Search** – Run a few example queries and print the **top 5** chunks per query.

You should see:

- Upload counts and document IDs.
- Parse status / “waiting for parsing…” then completion.
- For each query: the returned chunk texts (and optionally similarity scores).

That’s the full path: **workspace files → RAGFlow dataset → parsing → retrieval in meta-factory**.

---

## 4. How it threads into the rest of the app

- **`librarian/rag_client.py`** – Talks to RAGFlow (create dataset, upload, parse status, search). Used by the Librarian and by agents.
- **`librarian/librarian.py`** – `sync_workspace()` uses the RAG client to push `workspace/` into RAGFlow; `get_rag_passages()` uses it to run searches (e.g. for agents).
- **`agents/tools/rag_search.py`** – Tool agents can call to query the same dataset with a similarity threshold.
- **Config** – `config.py` and `.env` (e.g. `META_FACTORY_RAGFLOW_*`) control URL, API key, dataset name, and timeouts.

So: **no agent reads raw files**; they use the Librarian (and thus RAGFlow) or the `rag_search` tool. The “source of truth” for ingested content is the RAGFlow dataset fed by `sync_workspace()`.

---

## 5. Troubleshooting

| Issue | What to check |
|-------|----------------|
| “Connection refused” to 9380 | RAGFlow containers are up: `docker compose -f ragflow/docker/docker-compose.yml ps`. Backend service should listen on 9380. |
| “Unauthorized” / 401 | API key in `.env` matches the one in RAGFlow UI (Avatar → API). No extra spaces; use `META_FACTORY_RAGFLOW_API_KEY`. |
| “list datasets failed” or “create dataset failed” | Same as above; also confirm `META_FACTORY_RAGFLOW_API_URL` is exactly the base URL (e.g. `http://localhost:9380` with no trailing path). |
| Sync works but search returns nothing | Wait for parsing to finish (the demo script waits; if you run sync manually, wait a bit or poll status). In RAGFlow UI: confirm the dataset has documents and chunks after parsing. If retrieval still returns no chunks, the API may return “Model not authorized” — in RAGFlow go to **Settings** (or dataset settings) and ensure an **embedding model** is configured and authorized for your tenant. |
| Parsing never finishes | Check RAGFlow/Elasticsearch logs in Docker. On Linux, ensure `vm.max_map_count` is set (step 1.1). |

---

## 6. Optional: run RAGFlow in the background

To stop RAGFlow later:

```bash
cd ragflow/docker
docker compose down
```

To start again:

```bash
cd ragflow/docker
docker compose up -d
```

Your dataset and API key persist in RAGFlow’s data volumes until you remove them or the volumes.
