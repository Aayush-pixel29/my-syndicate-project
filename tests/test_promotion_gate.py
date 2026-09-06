import unittest
from syndicate.learning.promotion_gate import PromotionGate, PromotionDecision
from syndicate.learning.skill import Skill


class TestPromotionGate(unittest.TestCase):
    def setUp(self):
        self.gate = PromotionGate()
        self.skill = Skill(
            skill_id="test-skill-v1",
            name="Test Skill",
            description="Test description",
            trigger="TestTrigger",
            procedure=["tool1", "tool2"],
            source_trajectory_id="traj-source-1",
            failure_type="wrong_tool_sequence",
            evidence=["Evidence 1"],
            version=1,
            validated=False,
            promoted=False
        )

    def test_promoted_when_score_improves_and_equal_tool_calls(self):
        baseline_eval = {"overall_score": 0.4}
        replay_eval = {"overall_score": 0.9}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=3,
            replay_tool_call_count=3
        )

        self.assertTrue(decision.promoted)
        self.assertAlmostEqual(decision.baseline_score, 0.4)
        self.assertAlmostEqual(decision.replay_score, 0.9)
        self.assertAlmostEqual(decision.score_delta, 0.5)
        self.assertEqual(decision.baseline_tool_calls, 3)
        self.assertEqual(decision.replay_tool_calls, 3)
        self.assertTrue(decision.metrics["score_improved"])
        self.assertFalse(decision.metrics["tool_efficiency_improved"])
        self.assertEqual(decision.metrics["tool_call_delta"], 0)
        self.assertIn("promoted", decision.reason.lower())

    def test_promoted_when_score_improves_and_fewer_tool_calls(self):
        baseline_eval = {"overall_score": 0.3}
        replay_eval = {"overall_score": 0.85}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=5,
            replay_tool_call_count=2
        )

        self.assertTrue(decision.promoted)
        self.assertAlmostEqual(decision.score_delta, 0.55)
        self.assertTrue(decision.metrics["tool_efficiency_improved"])
        self.assertEqual(decision.metrics["tool_call_delta"], -3)
        self.assertIn("promoted", decision.reason.lower())

    def test_rejected_when_no_score_improvement(self):
        baseline_eval = {"overall_score": 0.7}
        replay_eval = {"overall_score": 0.7}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=3,
            replay_tool_call_count=3
        )

        self.assertFalse(decision.promoted)
        self.assertAlmostEqual(decision.score_delta, 0.0)
        self.assertFalse(decision.metrics["score_improved"])
        self.assertIn("rejected", decision.reason.lower())
        self.assertIn("did not strictly improve", decision.reason.lower())

    def test_rejected_when_score_regression(self):
        baseline_eval = {"overall_score": 0.8}
        replay_eval = {"overall_score": 0.5}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=3,
            replay_tool_call_count=2
        )

        self.assertFalse(decision.promoted)
        self.assertAlmostEqual(decision.score_delta, -0.3)
        self.assertFalse(decision.metrics["score_improved"])
        self.assertIn("rejected", decision.reason.lower())

    def test_rejected_when_tool_calls_increase_despite_score_improvement(self):
        baseline_eval = {"overall_score": 0.5}
        replay_eval = {"overall_score": 0.9}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=2,
            replay_tool_call_count=4
        )

        self.assertFalse(decision.promoted)
        self.assertTrue(decision.metrics["score_improved"])
        self.assertEqual(decision.metrics["tool_call_delta"], 2)
        self.assertIn("rejected", decision.reason.lower())
        self.assertIn("more tool calls", decision.reason.lower())

    def test_rejected_when_both_score_and_tool_regression(self):
        baseline_eval = {"overall_score": 0.6}
        replay_eval = {"overall_score": 0.4}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=2,
            replay_tool_call_count=5
        )

        self.assertFalse(decision.promoted)
        self.assertFalse(decision.metrics["score_improved"])
        self.assertEqual(decision.metrics["tool_call_delta"], 3)
        self.assertIn("rejected", decision.reason.lower())
        self.assertIn("did not improve", decision.reason.lower())
        self.assertIn("tool usage increased", decision.reason.lower())

    def test_invalid_skill_raises_value_error(self):
        self.skill.skill_id = ""
        with self.assertRaises(ValueError):
            self.gate.decide(
                skill=self.skill,
                baseline_evaluation={"overall_score": 0.3},
                replay_evaluation={"overall_score": 0.8},
                baseline_tool_call_count=2,
                replay_tool_call_count=2
            )

    def test_skill_is_not_mutated(self):
        baseline_eval = {"overall_score": 0.4}
        replay_eval = {"overall_score": 0.9}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=2,
            replay_tool_call_count=2
        )

        self.assertTrue(decision.promoted)
        # Original skill object must remain unchanged
        self.assertFalse(self.skill.promoted)

    def test_exact_deltas_and_metrics_calculation(self):
        baseline_eval = {"overall_score": 0.35}
        replay_eval = {"overall_score": 0.75}
        decision = self.gate.decide(
            skill=self.skill,
            baseline_evaluation=baseline_eval,
            replay_evaluation=replay_eval,
            baseline_tool_call_count=6,
            replay_tool_call_count=4
        )

        self.assertAlmostEqual(decision.score_delta, 0.40)
        self.assertEqual(decision.metrics["score_delta"], 0.40)
        self.assertEqual(decision.metrics["tool_call_delta"], -2)
        self.assertTrue(decision.metrics["score_improved"])
        self.assertTrue(decision.metrics["tool_efficiency_improved"])

    def test_deterministic_output(self):
        baseline_eval = {"overall_score": 0.4}
        replay_eval = {"overall_score": 0.8}

        d1 = self.gate.decide(self.skill, baseline_eval, replay_eval, 3, 3)
        d2 = self.gate.decide(self.skill, baseline_eval, replay_eval, 3, 3)

        self.assertEqual(d1, d2)


if __name__ == "__main__":
    unittest.main()
