import unittest

from alpha_agent.config import ModelConfig
from alpha_agent.planner import HeuristicPlanner, OpenAIJsonPlanner


class HeuristicPlannerTests(unittest.TestCase):
    def test_stop_when_budget_exhausted(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide({"remaining_budget": 0})
        self.assertEqual(action.action, "stop")

    def test_seed_first_when_seed_queue_exists(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide(
            {
                "research_stage": "explore",
                "remaining_budget": 5,
                "seed_queue_remaining": 10,
                "seed_target_remaining": 4,
                "iteration": 1,
                "refine_candidates_available": 3,
                "diversification_candidates_available": 2,
            }
        )
        self.assertEqual(action.action, "evaluate_seed")
        self.assertGreaterEqual(action.batch_size, 1)
        self.assertTrue(action.hypothesis)

    def test_refine_when_seed_target_done(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide(
            {
                "research_stage": "exploit",
                "remaining_budget": 5,
                "seed_queue_remaining": 0,
                "seed_target_remaining": 0,
                "iteration": 4,
                "refine_candidates_available": 6,
                "diversification_candidates_available": 8,
            }
        )
        self.assertEqual(action.action, "evaluate_refine")

    def test_robustness_stage_prefers_robustness_action(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide(
            {
                "research_stage": "robustness",
                "remaining_budget": 6,
                "robustness_candidates_available": 4,
                "refine_candidates_available": 8,
                "seed_queue_remaining": 0,
                "seed_target_remaining": 0,
                "iteration": 5,
            }
        )
        self.assertEqual(action.action, "evaluate_robustness")

    def test_robustness_stage_does_not_auto_submit_before_harvest(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide(
            {
                "research_stage": "robustness",
                "remaining_budget": 6,
                "submission_mode": "auto_approved",
                "best_submittable_alpha_id": "A123",
                "robustness_candidates_available": 4,
                "refine_candidates_available": 0,
                "seed_queue_remaining": 0,
                "seed_target_remaining": 0,
                "iteration": 5,
            }
        )
        self.assertEqual(action.action, "evaluate_robustness")

    def test_robustness_stage_repairs_correlation_before_harvest(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide(
            {
                "research_stage": "robustness",
                "remaining_budget": 6,
                "robustness_candidates_available": 4,
                "refine_candidates_available": 8,
                "best_submittable_alpha_id": None,
                "failed_check_histogram": [{"check": "PROD_CORRELATION", "count": 3}],
                "seed_queue_remaining": 0,
                "seed_target_remaining": 0,
                "iteration": 5,
            }
        )
        self.assertEqual(action.action, "evaluate_refine")

    def test_harvest_auto_submit(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide(
            {
                "research_stage": "harvest",
                "remaining_budget": 3,
                "submission_mode": "auto_approved",
                "best_submittable_alpha_id": "A123",
            }
        )
        self.assertEqual(action.action, "submit_best")
        self.assertEqual(action.target_alpha_id, "A123")


class OpenAIPlannerFallbackTests(unittest.TestCase):
    def test_missing_api_key_falls_back_to_heuristic(self) -> None:
        planner = OpenAIJsonPlanner(
            ModelConfig(
                provider="openai",
                api_key_env="THIS_ENV_KEY_DOES_NOT_EXIST_ANYWHERE",
            )
        )
        action = planner.decide(
            {
                "research_stage": "explore",
                "remaining_budget": 5,
                "seed_queue_remaining": 5,
                "seed_target_remaining": 5,
                "iteration": 1,
            }
        )
        self.assertEqual(action.action, "evaluate_seed")


if __name__ == "__main__":
    unittest.main()
