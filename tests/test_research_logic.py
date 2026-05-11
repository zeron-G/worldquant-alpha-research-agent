import unittest

import alpha_research_pipeline as pipeline
from alpha_agent.research_logic import (
    ResearchNotebook,
    build_correlation_repair_candidates,
    expression_novelty,
)


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

    def test_correlation_failure_blocks_submit_ready(self) -> None:
        payload = {
            "is": {
                "checks": [
                    {"name": "LOW_SHARPE", "result": "PASS"},
                    {"name": "LOW_FITNESS", "result": "PASS"},
                    {"name": "PROD_CORRELATION", "result": "FAIL", "limit": 0.7, "value": 0.91},
                ]
            }
        }
        self.assertEqual(pipeline.failed_blocking_checks(payload), [])
        self.assertEqual(pipeline.failed_submission_checks(payload), ["PROD_CORRELATION"])
        record = {
            "status": "ok",
            "failed_blocking_checks": [],
            "failed_correlation_checks": ["PROD_CORRELATION"],
            "summary": {"pending": []},
        }
        self.assertFalse(pipeline.record_is_submit_ready(record))
        self.assertTrue(pipeline.record_quality_ready(record))

    def test_score_result_penalizes_correlation_failure(self) -> None:
        detail = {
            "is": {
                "sharpe": 1.4,
                "fitness": 1.0,
                "turnover": 0.25,
                "returns": 0.08,
                "drawdown": 0.03,
                "margin": 0.0008,
            }
        }
        passing_payload = {
            "is": {
                "checks": [
                    {"name": "LOW_SHARPE", "result": "PASS"},
                    {"name": "LOW_FITNESS", "result": "PASS"},
                    {"name": "PROD_CORRELATION", "result": "PASS", "limit": 0.7, "value": 0.55},
                ]
            }
        }
        failing_payload = {
            "is": {
                "checks": [
                    {"name": "LOW_SHARPE", "result": "PASS"},
                    {"name": "LOW_FITNESS", "result": "PASS"},
                    {"name": "PROD_CORRELATION", "result": "FAIL", "limit": 0.7, "value": 0.91},
                ]
            }
        }
        self.assertGreater(
            pipeline.score_result(detail, passing_payload),
            pipeline.score_result(detail, failing_payload) + 500,
        )

    def test_correlation_repair_candidates_generated_for_quality_frontier(self) -> None:
        record = {
            "status": "ok",
            "family": "social_price_combo",
            "idea_name": "combo",
            "candidate_key": "parent",
            "expression": "ts_mean(-scl12_buzz, 9) + rank((ts_mean(close, 26) - close) / close)",
            "settings": pipeline.normalize_settings({"neutralization": "SECTOR", "decay": 0}),
            "score": 700,
            "failed_correlation_checks": ["PROD_CORRELATION"],
            "metadata": {},
        }
        candidates = build_correlation_repair_candidates([record], family_filter=set())
        self.assertTrue(candidates)
        self.assertTrue(any(item.metadata.get("correlation_repair") for item in candidates))
        self.assertTrue(any(item.stage == "repair_correlation_combo" for item in candidates))


if __name__ == "__main__":
    unittest.main()
