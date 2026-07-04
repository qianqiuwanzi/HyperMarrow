"""Re-export shim — canonical implementation lives in learning_core."""
from learning_core.meta_learner import MetaLearner, SkillExtractor

__all__ = ["MetaLearner", "SkillExtractor"]
