# Procedural Memory System
# Function: Automate high-frequency rules into "muscle memory" (habits)
# This enables rules to be followed automatically without conscious thought

import sys
import json

# Safe UTF-8 setup (Python 3.7+ compatible, does not replace stdout globally)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass  # stdout.reconfigure not available on all platforms, benign
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Import memory_core config
from .config import get_workspace, get_memory_dir


class ProceduralMemory:
    """
    程序性记忆系统
    
    目标：将高频规则内化为"习惯"，减少决策检查点的提醒频率
    
    自动化等级：
    - Level 1: 需要提醒（手动检查）
    - Level 2: 偶尔提醒（80%+ 成功率）
    - Level 3: 很少提醒（90%+ 成功率）
    - Level 4: 基本自动（95%+ 成功率）
    - Level 5: 完全自动（99%+ 成功率，无需提醒）
    
    晋升规则：
    - 验证次数 >= 5 且 成功率 >= 90% → Level 4
    - 验证次数 >= 10 且 成功率 >= 95% → Level 5
    - 连续失败 2 次 → Level - 1（降级）
    """
    
    def __init__(self, workspace=None):
        if workspace is None:
            workspace = get_workspace()
        self.workspace = Path(workspace)
        self.memory_file = self.workspace / "memory" / "procedural_memory.json"
        self.rules_file = self.workspace / "memory" / "working_rules.md"
        
        # Initialize memory data
        self.data = self._load_or_init()
        
    def _load_or_init(self) -> Dict:
        """Load existing data or initialize new"""
        if self.memory_file.exists():
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Initialize new procedural memory
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "rules": {},
            "automation_levels": {
                "1": "需要提醒",
                "2": "偶尔提醒",
                "3": "很少提醒",
                "4": "基本自动",
                "5": "完全自动"
            }
        }
    
    def _save(self):
        """Save data to file"""
        self.data["updated_at"] = datetime.now().isoformat()
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_rule(self, rule_id: str, rule_name: str, context_patterns: List[str], 
                 description: str = "") -> Dict:
        """
        添加新规则到程序性记忆
        
        Args:
            rule_id: 规则唯一标识（如 "rule_001"）
            rule_name: 规则名称
            context_patterns: 触发上下文模式（如 ["daily-video-factory", "P2b"]）
            description: 规则描述
        
        Returns:
            规则数据
        """
        rule = {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "description": description,
            "context_patterns": context_patterns,
            "level": 1,  # 默认 Level 1（需要提醒）
            "success_count": 0,
            "failure_count": 0,
            "total_attempts": 0,
            "success_rate": 0.0,
            "consecutive_success": 0,
            "consecutive_failure": 0,
            "created_at": datetime.now().isoformat(),
            "last_used_at": None,
            "promoted_at": None,
            "demoted_at": None,
            "notes": []
        }
        
        self.data["rules"][rule_id] = rule
        self._save()
        
        return rule
    
    def record_outcome(self, rule_id: str, success: bool, context: str = "", 
                       note: str = "") -> Dict:
        """
        记录规则执行结果
        
        Args:
            rule_id: 规则标识
            success: 是否成功
            context: 触发上下文
            note: 备注
        
        Returns:
            更新后的规则数据
        """
        if rule_id not in self.data["rules"]:
            raise ValueError(f"Rule not found: {rule_id}")
        
        rule = self.data["rules"][rule_id]
        rule["total_attempts"] += 1
        rule["last_used_at"] = datetime.now().isoformat()
        
        if success:
            rule["success_count"] += 1
            rule["consecutive_success"] += 1
            rule["consecutive_failure"] = 0
        else:
            rule["failure_count"] += 1
            rule["consecutive_failure"] += 1
            rule["consecutive_success"] = 0
        
        # Calculate success rate
        rule["success_rate"] = rule["success_count"] / rule["total_attempts"]
        
        # Add note if provided
        if note:
            rule["notes"].append({
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "context": context,
                "note": note
            })
        
        # Check for level changes
        old_level = rule["level"]
        new_level = self._calculate_new_level(rule)
        
        if new_level != old_level:
            if new_level > old_level:
                rule["promoted_at"] = datetime.now().isoformat()
                rule["level"] = new_level
                print(f"🎉 Rule promoted: {rule_id} Level {old_level} → Level {new_level}")
            else:
                rule["demoted_at"] = datetime.now().isoformat()
                rule["level"] = new_level
                print(f"⚠️ Rule demoted: {rule_id} Level {old_level} → Level {new_level}")
        
        self._save()
        return rule
    
    def _calculate_new_level(self, rule: Dict) -> int:
        """计算规则的自动化等级"""
        level = rule["level"]
        success_rate = rule["success_rate"]
        total = rule["total_attempts"]
        consecutive = rule["consecutive_success"]
        consecutive_fail = rule["consecutive_failure"]
        
        # 降级条件
        if consecutive_fail >= 2 and level > 1:
            return level - 1
        
        # 升级条件
        if total >= 10 and success_rate >= 0.95 and level < 5:
            return 5
        elif total >= 5 and success_rate >= 0.90 and level < 4:
            return 4
        elif total >= 3 and success_rate >= 0.85 and level < 3:
            return 3
        elif total >= 2 and success_rate >= 0.80 and level < 2:
            return 2
        
        return level
    
    def set_embedder(self, model):
        """
        设置语义嵌入模型（复用 P2 VectorMemoryDB 的 SentenceTransformer）。
        启用后，check_context 优先使用语义匹配。
        """
        self._embedder = model
        self._rule_embeddings = None  # Invalidate cache
        print(f"[ProceduralMemory] Embedder set: semantic matching enabled")

    def build_rule_embeddings(self) -> int:
        """预计算所有规则模式的嵌入向量。"""
        if not hasattr(self, '_embedder') or self._embedder is None:
            return 0
        rules = self.data.get("rules", {})
        if not rules:
            return 0

        patterns = []
        for rule in rules.values():
            patterns.append(" ".join(rule.get("context_patterns", [])))

        if not patterns:
            return 0

        try:
            embs = self._embedder.encode(patterns, show_progress_bar=False)
            self._rule_embeddings = np.array(embs)
            self._rule_ids = list(rules.keys())
            print(f"[ProceduralMemory] Rule embeddings built: {len(embs)} vectors")
            return len(embs)
        except Exception as e:
            print(f"[ProceduralMemory] Embedding build failed: {e}")
            return 0

    def semantic_check_context(self, context: str,
                                min_similarity: float = 0.3) -> List[Dict]:
        """
        语义匹配：使用嵌入向量余弦相似度匹配规则。

        Args:
            context: 上下文字符串
            min_similarity: 最低相似度阈值

        Returns:
            匹配的规则列表
        """
        if not hasattr(self, '_embedder') or self._embedder is None:
            return []
        if self._rule_embeddings is None:
            self.build_rule_embeddings()
        if self._rule_embeddings is None or len(self._rule_embeddings) == 0:
            return []

        try:
            q_vec = self._embedder.encode([context], show_progress_bar=False)[0]
            q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-8)
            idx_norm = self._rule_embeddings / (
                np.linalg.norm(self._rule_embeddings, axis=1, keepdims=True) + 1e-8)
            scores = np.dot(idx_norm, q_norm)

            rules = self.data["rules"]
            matches = []
            for i, score in enumerate(scores):
                if float(score) >= min_similarity and i < len(self._rule_ids):
                    rule_id = self._rule_ids[i]
                    rule = rules.get(rule_id)
                    if rule:
                        matches.append({
                            "rule_id": rule_id,
                            "rule_name": rule["rule_name"],
                            "level": rule["level"],
                            "level_description": self.data["automation_levels"].get(
                                str(rule["level"]), ""),
                            "success_rate": rule["success_rate"],
                            "total_attempts": rule["total_attempts"],
                            "last_used": rule["last_used_at"],
                            "semantic_score": round(float(score), 4),
                            "_match_method": "semantic",
                        })
            matches.sort(key=lambda x: (x["level"], x.get("semantic_score", 0)), reverse=True)
            return matches
        except Exception as e:
            print(f"[ProceduralMemory] Semantic match failed: {e}")
            return []

    def check_context(self, context: str) -> List[Dict]:
        """
        检查上下文，返回相关的程序性记忆规则。
        优先语义匹配，回退子串匹配。

        Args:
            context: 当前上下文字符串

        Returns:
            匹配的规则列表（按自动化等级排序）
        """
        # Try semantic matching first
        if hasattr(self, '_embedder') and self._embedder is not None:
            semantic = self.semantic_check_context(context)
            if semantic:
                return semantic

        # Fallback: substring matching
        matches = []
        for rule_id, rule in self.data["rules"].items():
            for pattern in rule["context_patterns"]:
                if pattern.lower() in context.lower():
                    matches.append({
                        "rule_id": rule_id,
                        "rule_name": rule["rule_name"],
                        "level": rule["level"],
                        "level_description": self.data["automation_levels"][str(rule["level"])],
                        "success_rate": rule["success_rate"],
                        "total_attempts": rule["total_attempts"],
                        "last_used": rule["last_used_at"],
                        "_match_method": "substring",
                    })
                    break

        matches.sort(key=lambda x: x["level"], reverse=True)
        return matches
    
    def get_recommendation(self, context: str) -> Optional[Dict]:
        """
        获取当前上下文的推荐规则
        
        Args:
            context: 当前上下文
        
        Returns:
            推荐的规则（Level 最高的匹配规则）
        """
        matches = self.check_context(context)
        
        if matches:
            # 返回 Level 最高的规则
            return matches[0]
        return None
    
    def get_automation_summary(self) -> Dict:
        """获取自动化等级统计"""
        summary = {
            "total_rules": len(self.data["rules"]),
            "by_level": {str(i): 0 for i in range(1, 6)},
            "automatic_rules": 0,  # Level 4+
            "needs_attention": []  # Level 1-2
        }
        
        for rule_id, rule in self.data["rules"].items():
            level = rule["level"]
            summary["by_level"][str(level)] += 1
            
            if level >= 4:
                summary["automatic_rules"] += 1
            elif level <= 2:
                summary["needs_attention"].append({
                    "rule_id": rule_id,
                    "rule_name": rule["rule_name"],
                    "level": level,
                    "success_rate": rule["success_rate"]
                })
        
        return summary
    
    def list_rules(self, min_level: int = 1, max_level: int = 5) -> List[Dict]:
        """列出指定等级范围的规则"""
        rules = []
        for rule_id, rule in self.data["rules"].items():
            if min_level <= rule["level"] <= max_level:
                rules.append({
                    "rule_id": rule_id,
                    "rule_name": rule["rule_name"],
                    "level": rule["level"],
                    "level_description": self.data["automation_levels"][str(rule["level"])],
                    "success_rate": rule["success_rate"],
                    "total_attempts": rule["total_attempts"],
                    "last_used": rule["last_used_at"]
                })
        
        rules.sort(key=lambda x: (x["level"], -x["success_rate"]), reverse=True)
        return rules
    
    def migrate_from_working_rules(self) -> int:
        """
        从 working_rules.md 迁移规则到程序性记忆
        
        Returns:
            迁移的规则数量
        """
        if not self.rules_file.exists():
            print("⚠️ working_rules.md not found, skipping migration")
            return 0
        
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse rules from working_rules.md
        import re
        rule_pattern = r'### 规则(\d+)：(.+?)\n(.+?)(?=### 规则|\Z)'
        matches = re.findall(rule_pattern, content, re.DOTALL)
        
        migrated = 0
        for rule_num, rule_name, rule_content in matches:
            rule_id = f"rule_{rule_num.zfill(3)}"
            
            # Skip if already exists
            if rule_id in self.data["rules"]:
                continue
            
            # Extract context patterns (if any)
            patterns = []
            if "daily-video-factory" in rule_content:
                patterns.append("daily-video-factory")
            if "P2b" in rule_content:
                patterns.append("P2b")
            if "scripts" in rule_content or "脚本" in rule_content:
                patterns.append("scripts")
            
            # Add rule
            self.add_rule(
                rule_id=rule_id,
                rule_name=f"规则{rule_num}：{rule_name.strip()}",
                context_patterns=patterns,
                description=rule_content[:200].strip()
            )
            
            migrated += 1
        
        print(f"✅ Migrated {migrated} rules from working_rules.md")
        return migrated
    
    def print_status(self):
        """打印当前状态"""
        summary = self.get_automation_summary()
        
        print("\n" + "="*50)
        print("  程序性记忆状态")
        print("="*50)
        print(f"  总规则数: {summary['total_rules']}")
        print(f"  自动规则: {summary['automatic_rules']} (Level 4+)")
        print("")
        print("  等级分布:")
        for level, desc in self.data["automation_levels"].items():
            count = summary["by_level"][level]
            bar = "█" * count
            print(f"    Level {level} ({desc}): {bar} {count}")
        
        if summary["needs_attention"]:
            print("")
            print("  ⚠️ 需要关注的规则:")
            for rule in summary["needs_attention"][:5]:
                print(f"    - {rule['rule_name']} (Level {rule['level']}, 成功率 {rule['success_rate']:.0%})")
        
        print("="*50 + "\n")


# CLI Interface
if __name__ == "__main__":
    import sys
    
    pm = ProceduralMemory()
    
    if len(sys.argv) < 2:
        # Show help
        print("""
程序性记忆系统 CLI

用法:
  python procedural_memory.py status                    # 显示状态
  python procedural_memory.py add <id> <name> <patterns> # 添加规则
  python procedural_memory.py record <id> <success>       # 记录结果
  python procedural_memory.py check <context>             # 检查上下文
  python procedural_memory.py list [min_level]           # 列出规则
  python procedural_memory.py migrate                    # 从 working_rules 迁移
  python procedural_memory.py recommend <context>         # 获取推荐

示例:
  python procedural_memory.py add rule_001 "使用技能脚本" "daily-video-factory,P2b"
  python procedural_memory.py record rule_001 true "P2b 下载成功"
  python procedural_memory.py check "daily-video-factory P2b 下载"
  python procedural_memory.py recommend "正在使用 daily-video-factory"
""")
        pm.print_status()
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        pm.print_status()
    
    elif cmd == "add":
        if len(sys.argv) < 5:
            print("用法: add <rule_id> <rule_name> <patterns_csv>")
            sys.exit(1)
        rule_id, rule_name = sys.argv[2], sys.argv[3]
        patterns = sys.argv[4].split(",")
        pm.add_rule(rule_id, rule_name, patterns)
        print(f"✅ Added rule: {rule_name}")
    
    elif cmd == "record":
        if len(sys.argv) < 4:
            print("用法: record <rule_id> <success> [note]")
            sys.exit(1)
        rule_id, success = sys.argv[2], sys.argv[3].lower() == "true"
        note = sys.argv[4] if len(sys.argv) > 4 else ""
        pm.record_outcome(rule_id, success, note=note)
        print(f"✅ Recorded outcome: {success}")
    
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("用法: check <context>")
            sys.exit(1)
        context = sys.argv[2]
        matches = pm.check_context(context)
        print(f"Context: {context}")
        print(f"Found {len(matches)} matching rules:")
        for m in matches:
            print(f"  [{m['level']}] {m['rule_name']} ({m['level_description']})")
    
    elif cmd == "list":
        min_level = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        rules = pm.list_rules(min_level=min_level)
        print(f"Rules (Level >= {min_level}):")
        for r in rules:
            print(f"  [{r['level']}] {r['rule_name']} - {r['success_rate']:.0%} ({r['total_attempts']}次)")
    
    elif cmd == "migrate":
        count = pm.migrate_from_working_rules()
        print(f"✅ Migrated {count} rules")
    
    elif cmd == "recommend":
        if len(sys.argv) < 3:
            print("用法: recommend <context>")
            sys.exit(1)
        context = sys.argv[2]
        rec = pm.get_recommendation(context)
        if rec:
            print(f"📋 推荐: {rec['rule_name']}")
            print(f"   Level: {rec['level']} ({rec['level_description']})")
            print(f"   成功率: {rec['success_rate']:.0%}")
        else:
            print("没有找到相关规则")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
