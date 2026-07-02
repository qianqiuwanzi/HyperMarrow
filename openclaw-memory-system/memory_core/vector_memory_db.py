# Vector Database Integration Script
# Function: Use ChromaDB for semantic memory search

# Set HF mirror for China BEFORE ANY import
from .config import setup_hf_mirror, get_memory_dir

setup_hf_mirror()

import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pathlib import Path
import numpy as np

# HF env already set above

class VectorMemoryDB:
    def __init__(self, db_path=None):
        """
        Initialize Vector Memory Database

        Args:
            db_path: Path to ChromaDB storage (default: <workspace>/memory/chromadb)
        """
        if db_path is None:
            db_path = get_memory_dir() / "chromadb"
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Initialize sentence transformer with mirror
        print("[VectorDB] Loading sentence transformer model...")
        print("[VectorDB] Using HF mirror: https://hf-mirror.com")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("[VectorDB] Model loaded successfully")
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="memory_vectors",
            metadata={"description": "OpenClaw memory vectors"}
        )
        
        print(f"[VectorDB] Collection has {self.collection.count()} vectors")
    
    def add_memory(self, memory_id, content, metadata=None):
        """
        Add memory to vector database
        
        Args:
            memory_id: Unique memory ID
            content: Text content to vectorize
            metadata: Additional metadata (dict)
        """
        if metadata is None:
            metadata = {}
        
        # Generate embedding
        embedding = self.model.encode(content).tolist()
        
        # Add to collection
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )
        
        print(f"[VectorDB] Added memory: {memory_id}")
    
    def search(self, query, n_results=5):
        """
        Semantic search in memory
        
        Args:
            query: Search query (string)
            n_results: Number of results to return
        
        Returns:
            results: List of matching memories
        """
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        print(f"[VectorDB] Found {len(results['ids'][0])} results for query: {query}")
        
        return results
    
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
                - collection_name: name of the ChromaDB collection
                - model_name: name of the embedding model
                - embedding_dim: dimension of each embedding vector
                - db_path: path to the ChromaDB storage
        """
        try:
            total = self.collection.count()
        except Exception:
            total = 0
        
        # Get embedding dimension from model
        try:
            sample_embedding = self.model.encode("test")
            embedding_dim = int(sample_embedding.shape[0])
        except Exception:
            embedding_dim = 384  # default for paraphrase-multilingual-MiniLM-L12-v2
        
        return {
            "total_vectors": total,
            "collection_name": self.collection.name,
            "model_name": self.model.model_name if hasattr(self.model, 'model_name') else 'paraphrase-multilingual-MiniLM-L12-v2',
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
