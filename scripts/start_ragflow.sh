#!/usr/bin/env bash
# One-off: start RAGFlow (Docker). Run once with Docker Desktop running.
# RAGFlow is expected at ../ragflow (sibling of meta-factory) or set RAGFLOW_ROOT.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
META_FACTORY_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RAGFLOW_ROOT="${RAGFLOW_ROOT:-$(cd "$META_FACTORY_ROOT/../ragflow" 2>/dev/null && pwd)}"

if [ -z "$RAGFLOW_ROOT" ] || [ ! -f "$RAGFLOW_ROOT/docker/docker-compose.yml" ]; then
  echo "RAGFlow not found at $META_FACTORY_ROOT/../ragflow"
  echo "Clone it first: git clone https://github.com/infiniflow/ragflow.git ../ragflow"
  echo "Or set RAGFLOW_ROOT=/path/to/ragflow"
  exit 1
fi

echo "RAGFlow root: $RAGFLOW_ROOT"
echo "Checking Docker..."
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop and run this script again."
  exit 1
fi

# macOS: set vm.max_map_count for Elasticsearch (one-off)
if [ "$(uname)" = "Darwin" ]; then
  echo "Setting vm.max_map_count (macOS)..."
  docker run --rm --privileged --pid=host alpine sysctl -w vm.max_map_count=262144 2>/dev/null || true
fi

echo "Starting RAGFlow (this may take a few minutes on first run)..."
cd "$RAGFLOW_ROOT/docker"
docker compose up -d

echo ""
echo "RAGFlow is starting. When ready:"
echo "  - UI:    http://127.0.0.1"
echo "  - API:   http://localhost:9380"
echo "  - Get API key: UI → Avatar (top right) → API"
echo "  - Add to meta-factory .env: META_FACTORY_RAGFLOW_API_KEY=<your-key>"
echo "  - Run demo: python scripts/rag_demo.py"
