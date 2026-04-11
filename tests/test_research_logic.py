import unittest

import alpha_research_pipeline as pipeline
from alpha_agent.research_logic import ResearchNotebook, expression_novelty


class ResearchLogicTests(unittest.TestCase):
    def test_expression_novelty_drops_for_similar_expression(self) -> None:
        frontier = [{"expression": "rank(ts_delta(close, 5))"}]
        novelty = expression_novelty(
            "rank(ts_delta(close, 5))",
            [set(["rank", "ts_delta", "close"])],
        )
        self.assertLess(novelty, 0.5)
        self.assertEqual(len(frontier), 1)

    def test_stage_transition_to_exploit_then_robustness(self) -> None:
        notebook = ResearchNotebook(
            budget=20,
            max_family_budget_share=0.5,
            min_expression_novelty=0.1,
            robustness_score_threshold=500.0,
        )
        stage, _ = notebook.determine_stage(
            iteration=1,
            evaluated_total=2,
            seed_target=10,
            leaderboard=[],
            records=[],
        )
        self.assertEqual(stage, "explore")
        stage, _ = notebook.determine_stage(
            iteration=4,
            evaluated_total=12,
            seed_target=10,
            leaderboard=[],
            records=[],
        )
        self.assertEqual(stage, "exploit")
        strong_record = {
            "status": "ok",
            "score": 620.0,
            "precheck_submit_ready": False,
        }
        stage, _ = notebook.determine_stage(
            iteration=5,
            evaluated_total=13,
            seed_target=10,
            leaderboard=[strong_record],
            records=[strong_record],
        )
        self.assertEqual(stage, "robustness")

    def test_rank_candidates_prefers_robustness_candidates_in_robust_stage(self) -> None:
        notebook = ResearchNotebook(
            budget=20,
            max_family_budget_share=0.5,
            min_expression_novelty=0.1,
            robustness_score_threshold=500.0,
        )
        settings = pipeline.normalize_settings({})
        plain = pipeline.Candidate(
            expression="rank(ts_delta(close, 5))",
            settings=settings,
            family="news_attention",
            idea_name="plain",
            stage="refine",
            priority=100.0,
            metadata={},
        )
        robust = pipeline.Candidate(
            expression="rank(ts_delta(close, 5))",
            settings=settings,
            family="news_attention",
            idea_name="robust",
            stage="robustness_universe",
            priority=95.0,
            metadata={"robustness": True},
        )
        ranked = notebook.rank_candidates(
            candidates=[plain, robust],
            frontier_records=[],
            stage="robustness",
            blocked_families=set(),
        )
        self.assertEqual(ranked[0].idea_name, "robust")


if __name__ == "__main__":
    unittest.main()
