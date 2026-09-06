import unittest
from syndicate.learning.failure_analyzer import FailureAnalyzer, FailureAnalysis


class TestFailureAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = FailureAnalyzer()
        
    def _assert_valid_analysis(self, analysis: FailureAnalysis):
        self.assertIsInstance(analysis.failure_type, str)
        self.assertIsInstance(analysis.root_cause, str)
        self.assertIsInstance(analysis.evidence, list)
        self.assertIsInstance(analysis.recommended_change, str)
        self.assertIsInstance(analysis.confidence, float)
        self.assertTrue(0.0 <= analysis.confidence <= 1.0)

    def test_successful_trajectory(self):
        trajectory = {
            "steps": [
                {"tool_name": "tool1", "input": {"a": 1}, "success": True},
            ],
            "final_answer": "Done."
        }
        evaluation = {
            "overall_score": 1.0,
            "category": "excellent",
            "details": {
                "efficiency": 1.0,
                "task_completeness": 1.0,
                "correctness": 1.0
            }
        }
        analysis = self.analyzer.analyze(trajectory, evaluation)
        self._assert_valid_analysis(analysis)
        self.assertEqual(analysis.failure_type, "none")

    def test_tool_failure(self):
        trajectory = {
            "tool_calls": [{"tool_name": "tool1", "input": {"a": 1}}],
            "tool_results": [{"success": False, "error": "Crash!"}],
            "final_answer": "Done."
        }
        evaluation = {
            "overall_score": 0.5,
            "category": "fair",
            "details": {}
        }
        analysis = self.analyzer.analyze(trajectory, evaluation)
        self._assert_valid_analysis(analysis)
        self.assertEqual(analysis.failure_type, "tool_failure")
        self.assertIn("Crash!", analysis.evidence[0])

    def test_incomplete_execution(self):
        trajectory = {
            "steps": [{"tool_name": "tool1", "input": {"a": 1}, "success": True}],
            "final_answer": None
        }
        evaluation = {
            "overall_score": 0.3,
            "category": "poor",
            "details": {
                "task_completeness": 0.5
            }
        }
        analysis = self.analyzer.analyze(trajectory, evaluation)
        self._assert_valid_analysis(analysis)
        self.assertEqual(analysis.failure_type, "incomplete_execution")

    def test_inefficient_sequence(self):
        trajectory = {
            "steps": [
                {"tool_name": "tool1", "input": {"a": 1}, "success": True},
                {"tool_name": "tool1", "input": {"a": 1}, "success": True},
            ],
            "final_answer": "Done."
        }
        evaluation = {
            "overall_score": 0.6,
            "category": "good",
            "details": {
                "efficiency": 0.4,
                "task_completeness": 1.0
            }
        }
        analysis = self.analyzer.analyze(trajectory, evaluation)
        self._assert_valid_analysis(analysis)
        self.assertEqual(analysis.failure_type, "inefficient_execution")

    def test_missing_evaluation(self):
        trajectory = {"steps": []}
        evaluation = {}
        analysis = self.analyzer.analyze(trajectory, evaluation)
        self._assert_valid_analysis(analysis)
        self.assertEqual(analysis.failure_type, "evaluation_failure")


if __name__ == "__main__":
    unittest.main()
