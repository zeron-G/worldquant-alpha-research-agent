import tempfile
import unittest
from pathlib import Path

import alpha_research_pipeline as pipeline


class FakeClient:
    def simulate(self, payload, *, max_wait, poll_interval):
        return {"alpha": "A_PROGRESS"}

    def fetch_alpha_detail(self, alpha_id):
        return {
            "id": alpha_id,
            "is": {
                "sharpe": 1.2,
                "fitness": 0.9,
                "turnover": 0.25,
                "returns": 0.05,
                "drawdown": 0.02,
                "margin": 0.0005,
            },
        }

    def check_alpha(self, alpha_id, *, max_wait, poll_interval):
        return {
            "is": {
                "checks": [
                    {"name": "LOW_SHARPE", "result": "PASS"},
                    {"name": "LOW_FITNESS", "result": "PASS"},
                    {"name": "PROD_CORRELATION", "result": "PASS"},
                ]
            }
        }


class ProgressCallbackTests(unittest.TestCase):
    def test_evaluate_batch_emits_candidate_progress(self) -> None:
        candidate = pipeline.Candidate(
            expression="rank(ts_delta(close, 5))",
            settings=pipeline.normalize_settings({}),
            family="price_reversion",
            idea_name="progress_test",
        )
        events = []
        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            records = pipeline.evaluate_batch(
                client=FakeClient(),
                candidates=[candidate],
                results_store=pipeline.JsonlStore(workdir / "results.jsonl"),
                submissions_store=pipeline.JsonlStore(workdir / "submissions.jsonl"),
                submitted_alpha_ids=set(),
                max_wait=1,
                poll_interval=0,
                retries=0,
                sleep_between=0,
                should_attempt_submit=False,
                allow_pending_checks=False,
                stop_on_submittable=False,
                submission_attempts=[],
                progress_callback=events.append,
            )

        self.assertEqual(len(records), 1)
        self.assertEqual([event["type"] for event in events], ["candidate_started", "candidate_completed"])
        self.assertEqual(events[1]["record"]["alpha_id"], "A_PROGRESS")


if __name__ == "__main__":
    unittest.main()
