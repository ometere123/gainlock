"""Small reproducible mutation checks for the protocol's critical guards.

Each mutation is executed against an in-memory copy of the contract source. A
test is killed when the corresponding independent invariant assertion fails on
the mutant. This is intentionally focused on the graph and semantic parsing
gates rather than a broad mutation-score claim for every line of the contract.
"""
import importlib.util
import pathlib
import sys
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "gainlock.py"
SUPPORT = ROOT / "tests" / "test_gainlock.py"


def load_support():
    spec = importlib.util.spec_from_file_location("gainlock_test_support", SUPPORT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_source(source: str, name: str):
    support = load_support()
    sdk = support.SDK()
    sys.modules["genlayer"] = sdk.mod
    module = types.ModuleType(name)
    exec(compile(source, str(CONTRACT), "exec"), module.__dict__)
    return module


class MutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CONTRACT.read_text(encoding="utf-8")

    def killed(self, mutant, assertion):
        module = load_source(mutant, "gainlock_mutant")
        with self.assertRaises(AssertionError):
            assertion(module)

    def test_omit_root_event_is_killed(self):
        mutant = self.source.replace(
            "total = 1\n        layers = [1]",
            "total = 0\n        layers = [0]", 1)
        self.killed(mutant, lambda m: self.assertEqual(
            m.bounded_analysis(3, [(0, 1, 1)], 1, 10)["root_totals"], [2, 1, 1]))

    def test_skip_last_depth_layer_is_killed(self):
        mutant = self.source.replace(
            "for _depth in range(max_hops):",
            "for _depth in range(max_hops - 1):", 1)
        self.killed(mutant, lambda m: self.assertEqual(
            m.bounded_analysis(1, [(0, 0, 1)], 2, 10)["root_totals"], [3]))

    def test_ignored_active_edge_is_killed(self):
        mutant = self.source.replace(
            "if current[a] and matrix[a][b]:",
            "if False:", 1)
        self.killed(mutant, lambda m: self.assertEqual(
            m.bounded_analysis(2, [(0, 1, 1)], 1, 10)["root_totals"], [2, 1]))

    def test_budget_bypass_is_killed(self):
        mutant = self.source.replace(
            '"admissible": maximum <= budget,',
            '"admissible": maximum >= 0,', 1)
        self.killed(mutant, lambda m: self.assertFalse(
            m.bounded_analysis(1, [(0, 0, 2)], 2, 3)["admissible"]))

    def test_format_error_as_uncertain_is_killed(self):
        mutant = self.source.replace(
            'return model_error("MALFORMED_RESULT")',
            'return {"relation": "UNCERTAIN", "reason": "MALFORMED_RESULT"}', 1)
        self.killed(mutant, lambda m: self.assertEqual(
            m._safe_result("not-json")["relation"], "MODEL_ERROR"))


if __name__ == "__main__":
    unittest.main()
