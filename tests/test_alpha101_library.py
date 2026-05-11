import json
import re
import unittest
from pathlib import Path

import alpha_research_pipeline as pipeline


ALPHA101_LIBRARY = Path("alpha101_ideas.json")


class Alpha101LibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.library = json.loads(ALPHA101_LIBRARY.read_text(encoding="utf-8"))

    def test_alpha101_library_has_all_seed_formulas(self) -> None:
        seeds = self.library["manual_seeds"]
        self.assertEqual(len(seeds), 101)
        self.assertEqual(seeds[0]["name"], "alpha101_001")
        self.assertEqual(seeds[-1]["name"], "alpha101_101")
        self.assertEqual(len({seed["name"] for seed in seeds}), 101)

    def test_alpha101_generates_unique_candidates_with_default_settings(self) -> None:
        fields = pipeline.load_available_fields("wqb_data_fields_summary.json")
        candidates = pipeline.generate_seed_candidates(
            library=self.library,
            family_filter={"alpha101"},
            available_fields=fields,
        )

        self.assertEqual(len(candidates), 101)
        self.assertEqual(len({candidate.signature() for candidate in candidates}), 101)
        self.assertTrue(all(candidate.family == "alpha101" for candidate in candidates))
        self.assertTrue(all(candidate.settings["decay"] == 0 for candidate in candidates))
        self.assertTrue(all(candidate.settings["neutralization"] == "INDUSTRY" for candidate in candidates))

    def test_alpha101_expressions_are_translated_to_fastexpr_style(self) -> None:
        legacy_patterns = [
            r"(?<!ts_)\bdelay\s*\(",
            r"(?<!ts_)\bdelta\s*\(",
            r"(?<!ts_)\bsum\s*\(",
            r"(?<!ts_)\bproduct\s*\(",
            r"(?<!ts_)\bstddev\s*\(",
            r"(?<!ts_)\bcorrelation\s*\(",
            r"(?<!ts_)\bcovariance\s*\(",
            r"\bIndClass\b",
            r"\bIndNeutralize\s*\(",
            r"\bSignedPower\s*\(",
            r"\badv(?!20\b)\d+\b",
        ]

        for seed in self.library["manual_seeds"]:
            expression = seed["expression"]
            self.assertEqual(
                expression.count("("),
                expression.count(")"),
                msg=f"Unbalanced parentheses in {seed['name']}",
            )
            for pattern in legacy_patterns:
                self.assertIsNone(
                    re.search(pattern, expression),
                    msg=f"{seed['name']} still contains legacy syntax matching {pattern}",
                )


if __name__ == "__main__":
    unittest.main()
