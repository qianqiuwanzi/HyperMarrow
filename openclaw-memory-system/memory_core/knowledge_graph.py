"""
Knowledge Graph — Entity-Relationship storage and graph queries.

Complements VectorMemoryDB: graph for structured relationships, vectors for semantics.
"""
import json
import sys as _sys
import uuid
from pathlib import Path
from collections import deque
from datetime import datetime
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
KG_FILE = DATA_DIR / "knowledge_graph.json"

# ── Optional spaCy NER ───────────────────────────────────────────────────────
_HAS_SPACY = False
_spacy_nlp = None
try:
    import spacy
    _spacy_nlp = spacy.load("zh_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
    _HAS_SPACY = True
except (ImportError, OSError):
    try:
        import spacy
        _spacy_nlp = spacy.load("en_core_web_sm", disable=["parser", "tagger", "lemmatizer"])
        _HAS_SPACY = True
    except (ImportError, OSError):
        pass

# Map spaCy entity labels to KnowledgeGraph entity types
_SPACY_LABEL_MAP = {
    "PERSON": "person", "ORG": "organization", "GPE": "location",
    "PRODUCT": "tool", "EVENT": "concept", "WORK_OF_ART": "concept",
    "DATE": "metadata", "TIME": "metadata", "MONEY": "metadata",
    "FAC": "location", "LOC": "location",
}

# Predefined entity type → keyword mapping for extraction
_TYPE_KEYWORDS = {
    "tool": [
        "daily-video-factory", "cover-generator", "deep-research",
        "html-ppt-to-video", "chromadb", "sentence-transformers",
        "python", "git", "numpy",
    ],
    "skill": [
        "cover-generator", "deep-research", "daily-video-factory",
        "html-ppt-to-video", "code-review", "simplify", "verify",
        "loop", "run",
    ],
    "concept": [
        "q-learning", "reinforcement-learning", "semantic-search",
        "embedding", "vector-database", "procedural-memory",
        "episodic-memory", "working-memory", "knowledge-graph",
        "transfer-learning", "ltp", "ltd", "memory-consolidation",
    ],
    "phase": [
        "P0", "P1", "P2", "P2a", "P2b", "P3", "P4", "P5",
    ],
    "error_type": [
        "import_error", "timeout", "download_stuck",
        "format_unsupported", "script_not_found", "network_error",
    ],
}


def _make_id() -> str:
    return str(uuid.uuid4())[:8]


def _now() -> str:
    return datetime.now().isoformat()


class KnowledgeGraph:
    """
    知识图谱 — 实体-关系存储与图查询。

    数据模型：
      Entity:       {id, name, type, properties, created_at, updated_at}
      Relationship: {id, source_id, target_id, relation_type, weight, metadata, created_at}

    与 VectorMemoryDB 互补：图用于结构化关系，向量用于语义检索。
    """

    def __init__(self, path=None):
        self.path = Path(path) if path else KG_FILE
        self.data = self._load_or_init()
        # Runtime indexes for O(1) lookups
        self._name_index: dict = {}       # (name, type) → entity_id
        self._adjacency: dict = {}        # entity_id → [(neighbor_id, rel), ...]
        self._build_indexes()
        print(f"[KnowledgeGraph] Loaded: {len(self.data['entities'])} entities, "
              f"{len(self.data['relationships'])} relationships", file=_sys.stderr)

    # ── Persistence ────────────────────────────────────────────────────────

    def _load_or_init(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    if isinstance(raw, dict) and "entities" in raw:
                        raw.setdefault("entity_type_index", {})
                        raw.setdefault("updated_at", _now())
                        return raw
            except (json.JSONDecodeError, OSError) as e:
                print(f"[KnowledgeGraph] Load failed, using defaults: {e}")
        return {
            "version": "1.0",
            "entities": {},
            "relationships": [],
            "entity_type_index": {},
            "created_at": _now(),
            "updated_at": _now(),
        }

    def _save(self):
        self.data["updated_at"] = _now()
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _build_indexes(self):
        """Rebuild name and adjacency indexes from raw data. O(E + R)."""
        self._name_index.clear()
        for eid, ent in self.data["entities"].items():
            # Compatible with both old format (name) and new format (label)
            name = ent.get("name") or ent.get("label", "")
            key = (name.lower(), ent.get("type", "unknown"))
            self._name_index[key] = eid

        self._adjacency.clear()
        for r in self.data["relationships"]:
            self._adjacency.setdefault(r["source_id"], []).append((r["target_id"], r))
            self._adjacency.setdefault(r["target_id"], []).append((r["source_id"], r))

    def _add_to_indexes(self, entity: dict):
        key = (entity["name"].lower(), entity["type"])
        self._name_index[key] = entity["id"]

    def _remove_from_indexes(self, entity_id: str, entity_type: str, entity_name: str):
        key = (entity_name.lower(), entity_type)
        self._name_index.pop(key, None)
        self._adjacency.pop(entity_id, None)

    # ── Entity CRUD ────────────────────────────────────────────────────────

    def add_entity(self, name: str, entity_type: str,
                   properties: dict = None) -> dict:
        """
        添加实体。同名同类型实体会更新而非重复创建。

        Returns:
            Entity dict (含自动生成的 id)
        """
        # Dedup: same name + same type → update existing (O(1) via name index)
        key = (name.lower(), entity_type)
        existing_id = self._name_index.get(key)
        existing = self.data["entities"].get(existing_id) if existing_id else None
        if existing:
            if properties:
                # Ensure properties field exists (backward compat)
                if "properties" not in existing:
                    existing["properties"] = {}
                existing["properties"].update(properties)
                existing["updated_at"] = _now()
                self._save()
            return existing

        eid = _make_id()
        entity = {
            "id": eid,
            "name": name,
            "type": entity_type,
            "properties": properties or {},
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.data["entities"][eid] = entity
        self.data.setdefault("entity_type_index", {}).setdefault(entity_type, []).append(eid)
        self._add_to_indexes(entity)
        self._save()
        print(f"[KnowledgeGraph] Entity added: [{entity_type}] {name} ({eid})")
        return entity

    def get_entity(self, entity_id: str) -> Optional[dict]:
        """按 ID 获取实体。"""
        return self.data["entities"].get(entity_id)

    def _find_entity_by_name(self, name: str, entity_type: str = None) -> Optional[dict]:
        """按名称查找实体（精确匹配）。"""
        candidates = self.data["entity_type_index"].get(entity_type, []) if entity_type \
            else list(self.data["entities"].keys())
        for eid in candidates:
            ent = self.data["entities"].get(eid)
            if ent and ent["name"] == name:
                return ent
        return None

    def find_entity(self, name: str, entity_type: str = None) -> Optional[dict]:
        """按名称查找实体（精确匹配，公开接口）。"""
        return self._find_entity_by_name(name, entity_type)

    def search_entities(self, query: str, limit: int = 10,
                         sort_by: str = "relevance") -> list:
        """
        搜索实体（支持相关性排序）。

        Args:
            query: 搜索关键词
            limit: 结果上限
            sort_by: "relevance" (词频×时效×重要性) | "name" (字母序)

        P0-3 relevance score = token_overlap×0.5 + recency×0.3 + importance×0.2
        """
        lc = query.lower()
        query_tokens = set(lc.split())
        now = datetime.now()
        results = []

        for ent in self.data["entities"].values():
            name_lc = ent["name"].lower()
            if lc not in name_lc:
                continue

            if sort_by == "relevance":
                # Token overlap
                name_tokens = set(name_lc.replace("-", " ").replace("_", " ").split())
                overlap = len(query_tokens & name_tokens) / max(len(query_tokens), 1)
                # Recency decay (1 day half-life)
                try:
                    updated = datetime.fromisoformat(ent.get("updated_at", ""))
                    age_hours = max(0, (now - updated).total_seconds() / 3600)
                    recency = 2.0 ** (-age_hours / 24)  # 1-day half-life
                except (ValueError, TypeError):
                    recency = 0.5
                # Importance from properties or degree
                importance = min(1.0, len(self._adjacency.get(ent["id"], [])) / 10.0)
                score = overlap * 0.5 + recency * 0.3 + importance * 0.2
                results.append((score, ent))
            else:
                results.append((0, ent))

        if sort_by == "relevance":
            results.sort(key=lambda x: x[0], reverse=True)

        return [ent for _, ent in results[:limit]]

    def update_entity(self, entity_id: str, properties: dict) -> bool:
        """更新实体属性。"""
        ent = self.data["entities"].get(entity_id)
        if not ent:
            return False
        ent["properties"].update(properties)
        ent["updated_at"] = _now()
        self._save()
        return True

    def delete_entity(self, entity_id: str) -> bool:
        """删除实体及其所有关联关系。"""
        if entity_id not in self.data["entities"]:
            return False
        ent = self.data["entities"].pop(entity_id)
        # Remove from type index
        etype = ent["type"]
        idx = self.data["entity_type_index"].get(etype, [])
        if entity_id in idx:
            idx.remove(entity_id)
        # Remove from runtime indexes
        self._remove_from_indexes(entity_id, etype, ent["name"])
        # Remove associated relationships and adjacency entries
        self.data["relationships"] = [
            r for r in self.data["relationships"]
            if r["source_id"] != entity_id and r["target_id"] != entity_id
        ]
        self._adjacency.pop(entity_id, None)
        for nid in list(self._adjacency.keys()):
            self._adjacency[nid] = [(n, r) for n, r in self._adjacency.get(nid, [])
                                    if r["source_id"] != entity_id and r["target_id"] != entity_id]
        self._save()
        print(f"[KnowledgeGraph] Entity deleted: [{ent['type']}] {ent['name']}")
        return True

    # ── Relationship CRUD ──────────────────────────────────────────────────

    def add_relationship(self, source_id: str, target_id: str,
                         relation_type: str, weight: float = 1.0,
                         metadata: dict = None) -> dict:
        """
        创建两个实体之间的关系。
        相同 source+target+type 会自动去重（更新 weight）。

        Returns:
            Relationship dict
        """
        # Validate entities exist
        if source_id not in self.data["entities"]:
            raise ValueError(f"Source entity '{source_id}' not found")
        if target_id not in self.data["entities"]:
            raise ValueError(f"Target entity '{target_id}' not found")

        # Dedup
        for rel in self.data["relationships"]:
            if (rel["source_id"] == source_id and
                    rel["target_id"] == target_id and
                    rel["relation_type"] == relation_type):
                rel["weight"] = max(rel["weight"], weight)
                rel["metadata"] = (rel.get("metadata") or {}) | (metadata or {})
                self._save()
                return rel

        rel = {
            "id": _make_id(),
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation_type,
            "weight": min(max(weight, 0.0), 1.0),
            "metadata": metadata or {},
            "created_at": _now(),
        }
        self.data["relationships"].append(rel)
        # Maintain adjacency index
        self._adjacency.setdefault(source_id, []).append((target_id, rel))
        self._adjacency.setdefault(target_id, []).append((source_id, rel))
        self._save()
        return rel

    def get_relationships(self, entity_id: str,
                          relation_type: str = None) -> list:
        """获取实体的所有关系（双向）。"""
        results = []
        for r in self.data["relationships"]:
            if r["source_id"] == entity_id or r["target_id"] == entity_id:
                if relation_type is None or r["relation_type"] == relation_type:
                    results.append(r)
        return results

    def delete_relationship(self, rel_id: str) -> bool:
        """删除关系。"""
        before = len(self.data["relationships"])
        self.data["relationships"] = [
            r for r in self.data["relationships"] if r["id"] != rel_id
        ]
        if len(self.data["relationships"]) < before:
            self._save()
            return True
        return False

    # ── Entity Extraction ──────────────────────────────────────────────────

    def extract_entities_ner(self, text: str) -> list:
        """
        使用 spaCy NER 从文本提取实体。

        Returns:
            [新创建或已存在的 Entity, ...] 或空列表（spaCy 不可用时）
        """
        if not _HAS_SPACY or _spacy_nlp is None:
            return []

        try:
            doc = _spacy_nlp(text[:1000])  # Limit to prevent OOM
            found = []
            seen = set()
            for ent in doc.ents:
                kg_type = _SPACY_LABEL_MAP.get(ent.label_, "concept")
                name = ent.text.strip()
                key = (name.lower(), kg_type)
                if key in seen:
                    continue
                seen.add(key)
                if len(name) >= 2:  # Skip single-character entities
                    entity = self.add_entity(name, kg_type)
                    found.append(entity)
            return found
        except Exception as e:
            print(f"[KnowledgeGraph] NER failed, falling back to keywords: {e}")
            return []

    def extract_entities_from_text(self, text: str) -> list:
        """
        从文本中提取实体（优先 spaCy NER，回退到关键词匹配）。

        Returns:
            [新创建或已存在的 Entity, ...]
        """
        # Try spaCy NER first
        if _HAS_SPACY:
            ner_results = self.extract_entities_ner(text)
            if ner_results:
                return ner_results

        # Fallback: keyword-based extraction
        lc = text.lower()
        found = []
        for entity_type, keywords in _TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in lc:
                    ent = self.add_entity(kw, entity_type)
                    found.append(ent)
        return found

    def extract_episode_entities(self, episode: dict) -> list:
        """
        从 EpisodicMemory 的 episode 提取实体。
        解析 context 字段中的 key、tags 列表和 what 文本。
        """
        text_parts = [episode.get("what", "")]
        ctx = episode.get("context", {})
        if isinstance(ctx, dict):
            text_parts.extend(str(v) for v in ctx.values() if isinstance(v, str))
        text_parts.extend(episode.get("tags", []))
        combined = " ".join(text_parts)
        return self.extract_entities_from_text(combined)

    # ── Relationship Inference ─────────────────────────────────────────────

    def infer_relationships(self, cooccurrence_window: int = 5) -> int:
        """
        从共现模式推断关系。

        扫描所有 episode 的创建时间线，在同一时间窗口内出现的 entity 对
        自动创建 "co_occurs_with" 关系。

        Returns:
            新创建的关系数量
        """
        # Collect all entity extraction events sorted by time
        # For simplicity, use entity updated_at as proxy for co-occurrence
        entities = sorted(
            self.data["entities"].values(),
            key=lambda e: e.get("updated_at", ""),
        )
        if len(entities) < 2:
            return 0

        added = 0
        for i in range(len(entities)):
            window_end = i + cooccurrence_window
            for j in range(i + 1, min(window_end, len(entities))):
                e1, e2 = entities[i], entities[j]
                # Skip same-type tool-tool or concept-concept (less informative)
                if e1["type"] == e2["type"] and e1["type"] in ("tool", "concept"):
                    continue
                try:
                    self.add_relationship(
                        e1["id"], e2["id"],
                        relation_type="co_occurs_with",
                        weight=0.5,
                    )
                    added += 1
                except ValueError:
                    pass

        if added:
            print(f"[KnowledgeGraph] Inferred {added} co-occurrence relationships")
        return added

    # ── Graph Queries ──────────────────────────────────────────────────────

    def _neighbors(self, entity_id: str) -> list:
        """Return [(neighbor_id, relationship), ...] — O(1) via adjacency index."""
        return self._adjacency.get(entity_id, [])

    def find_related(self, entity_id: str,
                     relation_types: list = None,
                     max_depth: int = 2) -> list:
        """
        BFS 搜索相关实体。

        Returns:
            [{"entity": Entity, "path": [Relationship], "distance": int}, ...]
        """
        if entity_id not in self.data["entities"]:
            return []

        visited = {entity_id}
        queue = deque([(entity_id, [], 0)])
        results = []

        while queue:
            current, path, dist = queue.popleft()
            if dist > max_depth:
                continue

            for neighbor_id, rel in self._neighbors(current):
                if neighbor_id in visited:
                    continue
                if relation_types and rel["relation_type"] not in relation_types:
                    continue
                visited.add(neighbor_id)
                new_path = path + [rel]
                results.append({
                    "entity": self.data["entities"][neighbor_id],
                    "path": new_path,
                    "distance": dist + 1,
                })
                if dist + 1 < max_depth:
                    queue.append((neighbor_id, new_path, dist + 1))

        return results

    def shortest_path(self, source_id: str, target_id: str) -> Optional[list]:
        """
        BFS 最短路径搜索。

        Returns:
            [Entity|Relationship 交替的路径] 或 None
        """
        if source_id not in self.data["entities"]:
            return None
        if target_id not in self.data["entities"]:
            return None
        if source_id == target_id:
            return [self.data["entities"][source_id]]

        visited = {source_id}
        queue = deque([(source_id, [self.data["entities"][source_id]])])

        while queue:
            current, path = queue.popleft()
            for neighbor_id, rel in self._neighbors(current):
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                new_path = path + [rel, self.data["entities"][neighbor_id]]
                if neighbor_id == target_id:
                    return new_path
                queue.append((neighbor_id, new_path))

        return None

    def get_central_entities(self, top_n: int = 10) -> list:
        """按度中心性返回最核心的实体。"""
        degree = {}
        for r in self.data["relationships"]:
            degree[r["source_id"]] = degree.get(r["source_id"], 0) + 1
            degree[r["target_id"]] = degree.get(r["target_id"], 0) + 1

        total_entities = max(len(self.data["entities"]), 1)
        ranked = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [{
            "entity": self.data["entities"].get(eid),
            "degree": deg,
            "centrality": round(deg / (total_entities - 1), 4) if total_entities > 1 else 0.0,
        } for eid, deg in ranked if eid in self.data["entities"]]

    def get_subgraph(self, entity_id: str, depth: int = 1) -> dict:
        """
        以某实体为中心的局部子图。

        Returns:
            {"entities": [...], "relationships": [...]}
        """
        if entity_id not in self.data["entities"]:
            return {"entities": [], "relationships": []}

        visited_entities = {entity_id}
        visited_rels = set()
        frontier = {entity_id}

        for _ in range(depth):
            next_frontier = set()
            for eid in frontier:
                for neighbor_id, rel in self._neighbors(eid):
                    visited_rels.add(rel["id"])
                    if neighbor_id not in visited_entities:
                        visited_entities.add(neighbor_id)
                        next_frontier.add(neighbor_id)
            frontier = next_frontier

        return {
            "entities": [self.data["entities"][eid] for eid in visited_entities],
            "relationships": [r for r in self.data["relationships"]
                              if r["id"] in visited_rels],
        }

    # ── Stats ──────────────────────────────────────────────────────────────

    # ── Type Hierarchy & Reasoning ─────────────────────────────────────────

    # Type hierarchy: child_type → parent_type
    _TYPE_HIERARCHY = {
        "tool": "entity",
        "skill": "entity",
        "concept": "entity",
        "phase": "entity",
        "error_type": "entity",
        "person": "entity",
        "organization": "entity",
        "location": "entity",
        "project": "entity",
        "metadata": "entity",
    }

    # Transitive relation chains: if A→B and B→C, then A→C
    _TRANSITIVE_RELATIONS = {"uses", "depends_on", "executes_in", "co_occurs_with",
                              "implemented_by", "triggers"}

    def get_type_ancestors(self, entity_type: str) -> list:
        """返回实体类型的所有祖先类型（自底向上）。"""
        ancestors = []
        current = entity_type
        while current in self._TYPE_HIERARCHY:
            parent = self._TYPE_HIERARCHY[current]
            if parent == current:
                break
            ancestors.append(parent)
            current = parent
        return ancestors

    def infer_transitive(self) -> int:
        """
        传递推理：A→B 且 B→C，推断 A→C。

        Returns:
            新创建的关系数量
        """
        added = 0
        # Build adjacency for transitive closure
        edges = {}
        for r in self.data["relationships"]:
            if r["relation_type"] in self._TRANSITIVE_RELATIONS:
                key = (r["source_id"], r["relation_type"])
                edges.setdefault(key, set()).add(r["target_id"])

        # Find 2-hop transitive paths
        for (src, rel_type), mids in edges.items():
            for mid in mids:
                mid_key = (mid, rel_type)
                if mid_key in edges:
                    for dst in edges[mid_key]:
                        if dst != src:  # No self-loops
                            try:
                                # Skip if direct relation already exists
                                already = False
                                for r in self.data["relationships"]:
                                    if (r["source_id"] == src and
                                            r["target_id"] == dst and
                                            r["relation_type"] == rel_type):
                                        already = True
                                        break
                                if not already:
                                    self.add_relationship(
                                        src, dst, rel_type,
                                        weight=0.3,  # Inferred relations have lower weight
                                        metadata={"inferred": True, "method": "transitive"},
                                    )
                                    added += 1
                            except ValueError:
                                pass

        if added:
            print(f"[KnowledgeGraph] Transitive inference: {added} new relationships")
        return added

    def infer_type_relationships(self) -> int:
        """
        类型层次推理：相同 parent_type 的实体之间创建 sibling 关系。
        """
        added = 0
        # Group entities by type
        by_type = {}
        for eid, ent in self.data["entities"].items():
            etype = ent["type"]
            by_type.setdefault(etype, []).append(eid)

        # Within each type, create co_occurs_with for entities not yet connected
        for etype, eids in by_type.items():
            for i in range(len(eids)):
                for j in range(i + 1, len(eids)):
                    # Check if already connected
                    connected = False
                    for r in self.data["relationships"]:
                        if (r["source_id"] == eids[i] and r["target_id"] == eids[j]) or \
                           (r["source_id"] == eids[j] and r["target_id"] == eids[i]):
                            connected = True
                            break
                    if not connected:
                        try:
                            self.add_relationship(
                                eids[i], eids[j], "co_occurs_with",
                                weight=0.2,
                                metadata={"inferred": True, "method": "type_sibling"},
                            )
                            added += 1
                        except ValueError:
                            pass

        if added:
            print(f"[KnowledgeGraph] Type inference: {added} sibling relationships")
        return added

    def reason(self) -> dict:
        """
        运行完整推理管线：传递推理 + 类型推理。

        Returns:
            {transitive, type_sibling}
        """
        return {
            "transitive": self.infer_transitive(),
            "type_sibling": self.infer_type_relationships(),
        }

    def get_orphan_entities(self) -> list:
        """返回没有任何关系的孤立实体列表。"""
        orphans = []
        for eid, ent in self.data["entities"].items():
            if eid not in self._adjacency or len(self._adjacency[eid]) == 0:
                orphans.append(ent)
        return orphans

    def get_stats(self) -> dict:
        """返回知识图谱统计信息。"""
        entities = self.data["entities"]
        rels = self.data["relationships"]
        type_counts = {}
        for e in entities.values():
            t = e["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        rel_type_counts = {}
        for r in rels:
            rt = r["relation_type"]
            rel_type_counts[rt] = rel_type_counts.get(rt, 0) + 1

        n = len(entities)
        max_edges = n * (n - 1) if n > 1 else 1
        central = self.get_central_entities(5)

        return {
            "total_entities": n,
            "total_relationships": len(rels),
            "entity_types": type_counts,
            "relationship_types": rel_type_counts,
            "density": round(len(rels) / max_edges, 6),
            "top_central": [{
                "name": c["entity"]["name"] if c["entity"] else "?",
                "degree": c["degree"],
            } for c in central],
            "newest_entity": max(entities.values(), key=lambda e: e["created_at"])["name"]
            if entities else None,
        }


# Example usage
if __name__ == "__main__":
    kg = KnowledgeGraph()

    # Add entities
    tool = kg.add_entity("daily-video-factory", "tool",
                         {"version": "20.0", "category": "video"})
    skill = kg.add_entity("cover-generator", "skill",
                          {"category": "design"})
    concept = kg.add_entity("semantic-search", "concept")
    phase = kg.add_entity("P2b", "phase")
    error = kg.add_entity("download_stuck", "error_type")

    # Add relationships
    kg.add_relationship(tool["id"], skill["id"], "uses", weight=0.9)
    kg.add_relationship(tool["id"], phase["id"], "executes_in", weight=1.0)
    kg.add_relationship(concept["id"], tool["id"], "implemented_by", weight=0.7)
    kg.add_relationship(error["id"], tool["id"], "occurs_in", weight=0.5)

    # Graph queries
    related = kg.find_related(tool["id"], max_depth=1)
    print(f"\nRelated to '{tool['name']}': {len(related)} entities")
    for r in related:
        print(f"  - [{r['entity']['type']}] {r['entity']['name']} "
              f"(distance={r['distance']})")

    path = kg.shortest_path(skill["id"], phase["id"])
    if path:
        print(f"\nShortest path '{skill['name']}' → '{phase['name']}':")
        for item in path:
            if "relation_type" in item:
                print(f"  --[{item['relation_type']}]--> ", end="")
            else:
                print(f"[{item['type']}] {item['name']}")

    central = kg.get_central_entities(5)
    print(f"\nTop central entities:")
    for c in central:
        print(f"  - {c['entity']['name']} (degree={c['degree']}, "
              f"centrality={c['centrality']})")

    stats = kg.get_stats()
    print(f"\nStats: {stats['total_entities']} entities, "
          f"{stats['total_relationships']} relationships, "
          f"density={stats['density']}")
    print(f"Entity types: {stats['entity_types']}")

    print("\n[KnowledgeGraph] Test passed!")
