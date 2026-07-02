#!/usr/bin/env python3
# Test vector search

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = 'D:/OpenClaw/workspace/.cache/huggingface/hub'
os.environ['HF_HOME'] = 'D:/OpenClaw/workspace/.cache/huggingface'

from vector_memory_db import VectorMemoryDB

db = VectorMemoryDB()

# Test queries
queries = [
    "daily-video-factory P2b 下载卡住",
    "错误处理流程",
    "切换技能失败",
    "jieba 分词问题"
]

print("\n" + "="*60)
print("SEMANTIC SEARCH TEST")
print("="*60)

for query in queries:
    print(f"\nQuery: {query}")
    results = db.search(query, n_results=2)
    
    if results['ids'][0]:
        for i, (id, doc, dist) in enumerate(zip(results['ids'][0], results['documents'][0], results['distances'][0]), 1):
            preview = doc[:100].replace('\n', ' ')
            print(f"  {i}. [{id}] dist={dist:.4f}")
            print(f"     {preview}...")
    else:
        print("  No results")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
