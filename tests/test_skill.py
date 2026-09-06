import unittest
from syndicate.learning.skill import Skill


class TestSkill(unittest.TestCase):
    def setUp(self):
        self.valid_data = {
            "skill_id": "sk-123",
            "name": "Fix Compile Error",
            "description": "Fixes a simple compile error by modifying the file.",
            "trigger": "CompileError",
            "procedure": ["Read file", "Modify file", "Compile"],
            "source_trajectory_id": "traj-xyz",
            "failure_type": "tool_failure",
            "evidence": ["Error text"]
        }

    def test_valid_creation_and_defaults(self):
        skill = Skill(**self.valid_data)
        self.assertEqual(skill.skill_id, "sk-123")
        self.assertEqual(skill.version, 1)
        self.assertFalse(skill.validated)
        self.assertFalse(skill.promoted)
        self.assertEqual(skill.metadata, {})

    def test_validation_success(self):
        skill = Skill(**self.valid_data)
        self.assertTrue(skill.validate())

    def test_validation_failure(self):
        # Missing procedure
        data = dict(self.valid_data)
        data["procedure"] = []
        skill = Skill(**data)
        self.assertFalse(skill.validate())
        
        # Empty skill_id
        data = dict(self.valid_data)
        data["skill_id"] = ""
        skill = Skill(**data)
        self.assertFalse(skill.validate())

        # Invalid version
        data = dict(self.valid_data)
        skill = Skill(**data)
        skill.version = 0
        self.assertFalse(skill.validate())

    def test_to_dict(self):
        skill = Skill(**self.valid_data)
        skill.metadata = {"author": "agent"}
        d = skill.to_dict()
        self.assertEqual(d["skill_id"], "sk-123")
        self.assertEqual(d["version"], 1)
        self.assertEqual(d["metadata"], {"author": "agent"})

    def test_from_dict(self):
        data = dict(self.valid_data)
        data["version"] = 2
        data["validated"] = True
        data["promoted"] = True
        data["metadata"] = {"key": "value"}
        
        skill = Skill.from_dict(data)
        self.assertEqual(skill.skill_id, "sk-123")
        self.assertEqual(skill.version, 2)
        self.assertTrue(skill.validated)
        self.assertTrue(skill.promoted)
        self.assertEqual(skill.metadata, {"key": "value"})
        self.assertTrue(skill.validate())

    def test_from_dict_missing_fields(self):
        data = dict(self.valid_data)
        del data["skill_id"]
        with self.assertRaisesRegex(ValueError, "Missing required field: skill_id"):
            Skill.from_dict(data)
            
    def test_from_dict_defaults(self):
        skill = Skill.from_dict(self.valid_data)
        self.assertEqual(skill.version, 1)
        self.assertFalse(skill.validated)
        self.assertFalse(skill.promoted)
        self.assertEqual(skill.metadata, {})


if __name__ == "__main__":
    unittest.main()
