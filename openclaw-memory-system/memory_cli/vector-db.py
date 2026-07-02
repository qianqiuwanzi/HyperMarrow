# Vector Memory Database CLI
# Function: Easy-to-use interface for vector memory search

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import argparse
from vector_memory_db import VectorMemoryDB

def main():
    parser = argparse.ArgumentParser(description="Vector Memory Database CLI")
    parser.add_argument("action", choices=["init", "search", "add", "batch", "status", "stats"],
                        help="Action to perform")
    parser.add_argument("--query", "-q", type=str, help="Search query")
    parser.add_argument("--id", "-i", type=str, help="Memory ID")
    parser.add_argument("--content", "-c", type=str, help="Memory content")
    parser.add_argument("--metadata", "-m", type=str, help="Metadata (JSON string)")
    parser.add_argument("--top", "-t", type=int, default=5, help="Number of results")
    
    args = parser.parse_args()
    
    # Initialize DB
    db = VectorMemoryDB()
    
    if args.action == "init":
        print("[OK] Initializing vector database...")
        print(f"[OK] Database path: {db.db_path}")
        print(f"[OK] Collection: {db.collection.name}")
        print(f"[OK] Total vectors: {db.collection.count()}")
    
    elif args.action == "search":
        if not args.query:
            print("[ERROR] Query required for search action")
            sys.exit(1)
        
        print(f"[SEARCH] Query: {args.query}")
        results = db.search(args.query, n_results=args.top)
        
        if results and results['ids'][0]:
            print(f"\n[OK] Found {len(results['ids'][0])} results:\n")
            for i, (mem_id, doc, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                similarity = 1 - distance
                print(f"{'='*50}")
                print(f"Result #{i+1}")
                print(f"  ID: {mem_id}")
                print(f"  Similarity: {similarity:.2%}")
                print(f"  Source: {metadata.get('source', metadata.get('source_file', 'unknown'))}")
                print(f"  Content: {doc[:200]}...")
                print()
        else:
            print("[INFO] No results found")
    
    elif args.action == "add":
        if not args.id or not args.content:
            print("[ERROR] ID and content required for add action")
            sys.exit(1)
        
        import json
        metadata = {}
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except:
                print("[ERROR] Invalid metadata JSON")
                sys.exit(1)
        
        db.add_memory(args.id, args.content, metadata)
        print(f"[OK] Added memory: {args.id}")
    
    elif args.action == "batch":
        print("[OK] Running batch import from memory files...")
        db.batch_add_from_files()
        print(f"[OK] Batch complete. Total vectors: {db.collection.count()}")
    
    elif args.action == "status":
        print(f"\n{'='*50}")
        print("  Vector Memory Database Status")
        print(f"{'='*50}")
        print(f"  Database path: {db.db_path}")
        print(f"  Collection: {db.collection.name}")
        print(f"  Total vectors: {db.collection.count()}")
        print(f"  Model: paraphrase-multilingual-MiniLM-L12-v2")
        print(f"{'='*50}\n")
    
    elif args.action == "stats":
        import json
        stats_file = db.db_path / "stats.json"
        
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print("[INFO] No stats file found. Run batch first.")

if __name__ == "__main__":
    main()
