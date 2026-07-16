/** 功能定义 — 所有功能按版本分级 */
window.FEATURES = [
  { id:'basic_memory',    name:'基础记忆',   icon:'🧠', plan:'free',       desc:'工作记忆、情景记忆、过程记忆、知识图谱' },
  { id:'knowledge_graph', name:'知识图谱',   icon:'🕸️', plan:'free',       desc:'实体关系网络可视化检索' },
  { id:'semantic_search', name:'语义搜索',   icon:'🔍', plan:'pro',        desc:'向量语义检索，跨记忆智能联想' },
  { id:'rl_decision',     name:'RL决策辅助', icon:'🎯', plan:'pro',        desc:'Q-Learning 强化学习决策引擎' },
  { id:'metacognition',   name:'元认知校准', icon:'📊', plan:'pro',        desc:'决策准确率追踪与自动校准' },
  { id:'vector_memory',   name:'向量记忆',   icon:'📐', plan:'enterprise', desc:'无限向量存储与高维检索' },
  { id:'cross_agent',     name:'跨Agent迁移',icon:'🔗', plan:'enterprise', desc:'知识跨Agent迁移学习' },
];

/** 版本层级 */
window.PLAN_LEVEL = { free:0, pro:1, enterprise:2 };

/** 工具函数 */
window.FeatureUtils = {
  /** 获取某套餐下所有可用功能 ID */
  getAvailable(plan) {
    const level = window.PLAN_LEVEL[plan] || 0;
    return window.FEATURES.filter(f => (window.PLAN_LEVEL[f.plan] || 0) <= level).map(f => f.id);
  },

  /** 判断某功能对某套餐是否可用 */
  isAvailable(featureId, plan) {
    const f = window.FEATURES.find(x => x.id === featureId);
    if (!f) return false;
    return (window.PLAN_LEVEL[f.plan] || 0) <= (window.PLAN_LEVEL[plan] || 0);
  },

  /** 获取解锁某功能所需的最低套餐 */
  getUpgradePlan(featureId, currentPlan) {
    const f = window.FEATURES.find(x => x.id === featureId);
    if (!f) return null;
    const need = window.PLAN_LEVEL[f.plan] || 0;
    const cur = window.PLAN_LEVEL[currentPlan] || 0;
    if (need <= cur) return null;
    return f.plan === 'pro' ? 'pro' : 'enterprise';
  },

  /** 功能中文名 */
  label(featureId) {
    const f = window.FEATURES.find(x => x.id === featureId);
    return f ? f.name : featureId;
  }
};
