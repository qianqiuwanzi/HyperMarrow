# Vector Database Integration Script
# Function: Use ChromaDB for semantic memory search

# Set HF mirror for China BEFORE ANY import
from .config import setup_hf_mirror, get_memory_dir
import sys as _sys

setup_hf_mirror()

import json
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# ── Lazy imports: chromadb + sentence-transformers are optional engine modules ──
_HAS_CHROMADB = False
_HAS_SENTENCE_TRANSFORMERS = False
_chromadb_import_error = None
_st_import_error = None

try:
    import chromadb
    _HAS_CHROMADB = True
except ImportError as e:
    _chromadb_import_error = str(e)

try:
    from sentence_transformers import SentenceTransformer  # noqa: F811 (used later)
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError as e:
    _st_import_error = str(e)

# HF env already set above

class VectorMemoryDB:
    def __init__(self, db_path=None):
        """
        Initialize Vector Memory Database (lazy: model not loaded until first use)

        Args:
            db_path: Path to ChromaDB storage (default: <workspace>/memory/chromadb)
        """
        if not _HAS_CHROMADB:
            self.client = None
            self.collection = None
            self._model = None
            self._model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
            self.db_path = Path(db_path) if db_path else get_memory_dir() / "chromadb"
            print(f"[VectorDB] UNAVAILABLE — chromadb not installed ({_chromadb_import_error})", file=_sys.stderr)
            return

        if db_path is None:
            db_path = get_memory_dir() / "chromadb"
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB (lightweight, no model)
        self.client = chromadb.PersistentClient(path=str(self.db_path))

        # Model: lazy loaded on first use
        self._model = None
        self._model_name = 'paraphrase-multilingual-MiniLM-L12-v2'

        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="memory_vectors",
            metadata={"description": "OpenClaw memory vectors"}
        )

        print(f"[VectorDB] Initialized (lazy). Collection has {self.collection.count()} vectors", file=_sys.stderr)
    
    def _ensure_model(self):
        """Lazy-load sentence transformer model (called before first encode)."""
        if self._model is not None:
            return
        if not _HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                f"sentence-transformers not installed ({_st_import_error}). "
                "Install the vector engine module to enable semantic search."
            )
        print("[VectorDB] Loading sentence transformer model...", file=_sys.stderr)
        print("[VectorDB] Using HF mirror: https://hf-mirror.com", file=_sys.stderr)
        self._model = SentenceTransformer(self._model_name)
        print("[VectorDB] Model loaded successfully", file=_sys.stderr)

    @staticmethod
    def is_available() -> bool:
        """Check if vector memory engine is installed."""
        return _HAS_CHROMADB and _HAS_SENTENCE_TRANSFORMERS
    
    def add_memory(self, memory_id, content, metadata=None):
        """
        Add memory to vector database with automatic temporal metadata.

        Args:
            memory_id: Unique memory ID
            content: Text content to vectorize
            metadata: Additional metadata (dict); created_at is auto-injected

        Metadata augmentation:
            - created_at: ISO timestamp (auto)
            - days_ago: float days since now (auto)
        """
        if metadata is None:
            metadata = {}

        # Auto-inject temporal metadata
        now_iso = datetime.now().isoformat()
        metadata.setdefault("created_at", now_iso)

        # Generate embedding
        self._ensure_model()
        embedding = self._model.encode(content).tolist()

        # Add to collection
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )

        print(f"[VectorDB] Added memory: {memory_id} (created_at={now_iso})")
    
    def search(self, query, n_results=5, days_filter=None, sort_by="relevance"):
        """
        Semantic search with optional temporal filtering.

        Args:
            query:           Search query (string)
            n_results:       Number of results to return
            days_filter:     int or float — if set, only return memories
                             created within the last `days_filter` days.
                             Example: days_filter=7  → last 7 days only
            sort_by:         "relevance" (default) or "recency"
                             recency sorts by created_at desc within matched results

        Returns:
            results: ChromaDB query result dict (ids, documents, metadatas, distances)
        """
        # Generate query embedding
        self._ensure_model()
        query_embedding = self._model.encode(query).tolist()

        # Temporal cutoff (Python-side filtering — ChromaDB where doesn't support ISO string $gte)
        cutoff = None
        if days_filter is not None:
            cutoff = datetime.now() - timedelta(days=float(days_filter))
            print(f"[VectorDB] Temporal filter: last {days_filter} days (cutoff={cutoff.isoformat()})")

        # Search (always fetch more when temporal filter active)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 5 if cutoff else n_results,
        )

        # Post-filter: apply days_filter + recency sort in Python
        if results and results.get("ids") and results["ids"][0]:
            ids     = results["ids"][0]
            docs    = results["documents"][0]
            metas   = results["metadatas"][0] if results.get("metadatas") else []
            dists   = results.get("distances", [[]])[0]

            # Apply temporal filter
            if cutoff:
                pairs = list(zip(ids, docs, metas, dists))
                filtered = []
                for mid, doc, meta, dist in pairs:
                    ts_str = meta.get("created_at", "") if meta else ""
                    try:
                        if ts_str and datetime.fromisoformat(ts_str) >= cutoff:
                            filtered.append((mid, doc, meta, dist))
                    except (ValueError, TypeError):
                        pass  # Skip records with unparseable timestamps
                ids, docs, metas, dists = [list(x) for x in zip(*filtered)] if filtered else ([], [], [], [])

            # Sort by recency
            if sort_by == "recency" and metas:
                pairs = list(zip(ids, docs, metas, dists))
                pairs.sort(key=lambda x: x[2].get("created_at", "") if x[2] else "", reverse=True)
                ids, docs, metas, dists = [list(x) for x in zip(*pairs)] if pairs else ([], [], [], [])

            # Trim to n_results
            results["ids"][0]         = ids[:n_results]
            results["documents"][0]    = docs[:n_results]
            results["metadatas"][0]   = metas[:n_results]
            if results.get("distances"):
                results["distances"][0] = dists[:n_results]

        n_found = len(results.get("ids", [[]])[0]) if results else 0
        print(f"[VectorDB] Found {n_found} results for query: {query}")

        return results

    def search_by_days(self, n_days: int, query: str = None, n_results: int = 10) -> dict:
        """
        Get memories from the last N days, optionally filtered by semantic query.

        Args:
            n_days:    Number of days to look back
            query:     Optional semantic query string (if None, returns all recent)
            n_results: Max results

        Returns:
            dict with keys: ids, documents, metadatas, distances
        """
        if query:
            return self.search(query, n_results=n_results, days_filter=n_days, sort_by="recency")
        else:
            # No semantic query: fetch all then filter by time
            results = self.collection.get(include=["documents", "metadatas"])
            ids   = results.get("ids", []) or []
            docs  = results.get("documents", []) or []
            metas = results.get("metadatas", []) or []

            cutoff = datetime.now() - timedelta(days=n_days)
            filtered = []
            for mid, doc, meta in zip(ids, docs, metas):
                ts_str = meta.get("created_at", "") if meta else ""
                try:
                    if ts_str and datetime.fromisoformat(ts_str) >= cutoff:
                        filtered.append((mid, doc, meta))
                except (ValueError, TypeError):
                    pass  # Skip unparseable timestamps

            filtered.sort(key=lambda x: x[2].get("created_at", "") if x[2] else "", reverse=True)
            filtered = filtered[:n_results]
            print(f"[VectorDB] search_by_days({n_days}d): found {len(filtered)} memories")
            return {
                "ids": [[mid for mid, _, _ in filtered]],
                "documents": [[doc for _, doc, _ in filtered]],
                "metadatas": [[meta for _, _, meta in filtered]],
                "distances": [[0.0] * len(filtered)],
            }

    def get_temporal_stats(self) -> dict:
        """
        Return temporal statistics across all memories.

        Returns:
            dict with: total, date_range, per_day, oldest, newest
        """
        if not _HAS_CHROMADB or self.collection is None:
            return {"total": 0, "available": False, "reason": "Vector engine not installed"}

        all_data = self.collection.get(include=["metadatas"])
        metadatas = all_data.get("metadatas", []) or []

        if not metadatas:
            return {"total": 0, "date_range": None, "per_day": {}}

        dates = []
        for m in metadatas:
            ts = m.get("created_at", "")
            if ts:
                try:
                    dates.append(datetime.fromisoformat(ts))
                except (ValueError, TypeError):
                    pass  # Skip unparseable timestamps

        if not dates:
            return {"total": len(metadatas), "date_range": None, "per_day": {}}

        dates.sort()
        from collections import Counter
        day_counts = Counter(d.date().isoformat() for d in dates)

        return {
            "total": len(metadatas),
            "oldest": dates[0].isoformat(),
            "newest": dates[-1].isoformat(),
            "date_range_days": (dates[-1] - dates[0]).days if len(dates) > 1 else 0,
            "per_day": dict(sorted(day_counts.items())),
        }
    
    def batch_add_from_files(self, memory_dir=None):
        """
        Batch add memories from markdown files

        Args:
            memory_dir: Directory containing memory files (default: <workspace>/memory)
        """
        if memory_dir is None:
            memory_dir = get_memory_dir()
        memory_path = Path(memory_dir)
        
        # Find all markdown files
        md_files = list(memory_path.glob("*.md"))
        
        print(f"[VectorDB] Found {len(md_files)} markdown files")
        
        for md_file in md_files:
            if md_file.name == "memory_index.json":
                continue
            
            # Read file
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract memory blocks
            import re
            memories = re.findall(r'## Promoted From Short-Term Memory.*?\((.*?)\)(.*?)(?=## Promoted|$)', content, re.DOTALL)
            
            if memories:
                for i, (source, mem_content) in enumerate(memories):
                    memory_id = f"{md_file.stem}_mem_{i}"
                    metadata = {
                        "source_file": md_file.name,
                        "source": source.strip(),
                        "date": source.strip()
                    }
                    
                    # Add to vector DB
                    self.add_memory(memory_id, mem_content, metadata)
            else:
                # Add entire file as one memory
                memory_id = f"{md_file.stem}_full"
                metadata = {
                    "source_file": md_file.name,
                    "type": "full_file"
                }
                
                # Truncate if too long
                if len(content) > 10000:
                    content = content[:10000]
                
                self.add_memory(memory_id, content, metadata)
        
        print(f"[VectorDB] Batch add complete. Total vectors: {self.collection.count()}")
    
    def analyze_similarities(self, memory_id, top_n=5):
        """
        Find similar memories to a given memory
        
        Args:
            memory_id: Memory ID to compare
            top_n: Number of similar memories to return
        
        Returns:
            similar_memories: List of similar memory IDs and distances
        """
        # Get the memory
        result = self.collection.get(ids=[memory_id], include=['embeddings', 'documents'])
        
        if not result['ids']:
            print(f"[VectorDB] Memory not found: {memory_id}")
            return None
        
        embedding = result['embeddings'][0]
        document = result['documents'][0]
        
        # Find similar
        similar = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_n + 1  # +1 because it will include itself
        )
        
        # Filter out self
        similar_ids = similar['ids'][0]
        similar_distances = similar['distances'][0]
        
        results = []
        for i, (sid, dist) in enumerate(zip(similar_ids, similar_distances)):
            if sid != memory_id:
                results.append({
                    "id": sid,
                    "distance": dist,
                    "document": similar['documents'][0][i]
                })
        
        return results

    def get_stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            dict with keys:
                - total_vectors: total number of stored vectors
                - available: whether vector engine is installed
                - collection_name: name of the ChromaDB collection
                - model_name: name of the embedding model
                - embedding_dim: dimension of each embedding vector
                - db_path: path to the ChromaDB storage
        """
        if not _HAS_CHROMADB or self.collection is None:
            return {
                "total_vectors": 0,
                "available": False,
                "reason": "Vector engine not installed. Download from Settings > Engine Modules."
            }

        try:
            total = self.collection.count()
        except Exception:
            total = 0
        
        # Get embedding dimension — use default, don't load model just for stats
        embedding_dim = 384  # paraphrase-multilingual-MiniLM-L12-v2 default
        
        return {
            "total_vectors": total,
            "collection_name": self.collection.name,
            "model_name": self._model_name if self._model is None else (self._model.model_name if hasattr(self._model, 'model_name') else self._model_name),
            "embedding_dim": embedding_dim,
            "db_path": str(self.db_path)
        }

# Example usage
if __name__ == "__main__":
    # Initialize database
    print("=" * 60)
    print("  Vector Memory Database v1.0")
    print("=" * 60)
    print()
    
    db = VectorMemoryDB()
    
    # Batch add memories
    print("\n[1/3] Batch adding memories from files...")
    db.batch_add_from_files()
    
    # Test search
    print("\n[2/3] Testing semantic search...")
    query = "daily-video-factory 错误处理"
    results = db.search(query, n_results=3)
    
    print("\nSearch results:")
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\n{i+1}. Source: {metadata.get('source', 'unknown')}")
        print(f"   Content preview: {doc[:100]}...")
    
    # Analyze similarities
    print("\n[3/3] Analyzing similarities...")
    if results['ids'][0]:
        first_id = results['ids'][0][0]
        similar = db.analyze_similarities(first_id, top_n=3)
        
        if similar:
            print(f"\nMemories similar to {first_id}:")
            for s in similar:
                print(f"  - {s['id']} (distance: {s['distance']:.4f})")
    
    print("\n" + "=" * 60)
    print("  Vector Database Ready!")
    print("=" * 60)
