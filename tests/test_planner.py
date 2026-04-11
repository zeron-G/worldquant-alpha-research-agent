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

    def test_refine_when_seed_target_done(self) -> None:
        planner = HeuristicPlanner()
        action = planner.decide(
            {
                "remaining_budget": 5,
                "seed_queue_remaining": 0,
                "seed_target_remaining": 0,
                "iteration": 4,
                "refine_candidates_available": 6,
                "diversification_candidates_available": 8,
            }
        )
        self.assertEqual(action.action, "evaluate_refine")


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
                "remaining_budget": 5,
                "seed_queue_remaining": 5,
                "seed_target_remaining": 5,
                "iteration": 1,
            }
        )
        self.assertEqual(action.action, "evaluate_seed")


if __name__ == "__main__":
    unittest.main()
