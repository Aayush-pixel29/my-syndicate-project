"""Tests for GitHub simulator."""

import unittest
from syndicate.core.simulator import GithubSimulator, GithubTool


class TestGithubSimulator(unittest.TestCase):
    """Test GithubSimulator."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = GithubSimulator()
        self.simulator.initialize()

    def test_initialization(self):
        """Test simulator initialization."""
        self.assertTrue(self.simulator.initialized)
        self.assertEqual(len(self.simulator._scenarios), 2)

    def test_get_repo_data(self):
        """Test getting repository data."""
        data = self.simulator._get_repo_data("repocli/test-ci")
        self.assertIsNotNone(data)
        self.assertIn("workflows", data)

    def test_list_workflow_runs(self):
        """Test listing workflow runs."""
        runs = self.simulator.list_workflow_runs("repocli/test-ci", "main")

        self.assertIsInstance(runs, list)
        self.assertGreater(len(runs), 0)
        self.assertIn("branch", runs[0])
        self.assertIn("status", runs[0])

    def test_list_workflow_runs_default_branch(self):
        """Test listing workflow runs with default branch."""
        runs = self.simulator.list_workflow_runs("repocli/test-ci")
        # Should return runs for default branch (main)
        self.assertIsInstance(runs, list)

    def test_inspect_workflow_run(self):
        """Test inspecting workflow run."""
        runs = self.simulator.list_workflow_runs("repocli/test-ci")
        if runs:
            run_id = runs[0]["id"]
            result = self.simulator.inspect_workflow_run("repocli/test-ci", run_id)

            self.assertIn("id", result)
            self.assertIn("jobs", result)

    def test_inspect_workflow_run_not_found(self):
        """Test inspecting non-existent workflow run."""
        result = self.simulator.inspect_workflow_run("nonexistent", 999)
        self.assertIn("error", result)

    def test_inspect_job_logs(self):
        """Test inspecting job logs."""
        # First get a run with a job
        runs = self.simulator.list_workflow_runs("repocli/test-ci")
        if runs:
            run_id = runs[0]["id"]
            logs = self.simulator.inspect_job_logs("repocli/test-ci", run_id, "test")

            self.assertIn("Job: test", logs)
            self.assertIn("Status:", logs)

    def test_inspect_commit(self):
        """Test inspecting commit."""
        commit = self.simulator.inspect_commit("repocli/test-ci", "aaa111")

        self.assertEqual(commit["sha"], "aaa111")
        self.assertIn("message", commit)
        self.assertIn("author", commit)

    def test_inspect_commit_not_found(self):
        """Test inspecting non-existent commit."""
        result = self.simulator.inspect_commit("repocli/test-ci", "invalid")
        self.assertIn("error", result)

    def test_inspect_pull_request(self):
        """Test inspecting pull request."""
        pr = self.simulator.inspect_pull_request("repocli/test-ci", 123)

        self.assertEqual(pr["id"], 123)
        self.assertIn("title", pr)
        self.assertIn("state", pr)

    def test_inspect_pull_request_not_found(self):
        """Test inspecting non-existent pull request."""
        result = self.simulator.inspect_pull_request("repocli/test-ci", 99999)
        self.assertIn("error", result)

    def test_inspect_issue(self):
        """Test inspecting issue."""
        issue = self.simulator.inspect_issue("repocli/test-ci", 100)

        self.assertEqual(issue["id"], 100)
        self.assertIn("title", issue)
        self.assertIn("state", issue)

    def test_inspect_issue_not_found(self):
        """Test inspecting non-existent issue."""
        result = self.simulator.inspect_issue("repocli/test-ci", 99999)
        self.assertIn("error", result)

    def test_search_repository_commits(self):
        """Test searching repository commits."""
        results = self.simulator.search_repository("test", "repocli/test-ci")

        self.assertIsInstance(results, list)
        # Should find commits with "test" in message
        if results:
            self.assertIn("type", results[0])
            self.assertIn("sha", results[0])

    def test_search_repository_issues(self):
        """Test searching repository issues."""
        results = self.simulator.search_repository("bug", "repocli/test-ci")

        self.assertIsInstance(results, list)
        # Should find issues with "bug" in title
        if results:
            self.assertIn("type", results[0])
            self.assertIn("id", results[0])

    def test_search_repository_prs(self):
        """Test searching repository PRs."""
        results = self.simulator.search_repository("feature", "repocli/test-ci")

        self.assertIsInstance(results, list)
        # Should find PRs with "feature" in title
        if results:
            self.assertIn("type", results[0])
            self.assertIn("id", results[0])

    def test_search_repository_empty(self):
        """Test searching with no matches."""
        results = self.simulator.search_repository("nonexistent", "repocli/test-ci")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)


class TestGithubTool(unittest.TestCase):
    """Test GithubTool."""

    def setUp(self):
        """Set up test fixtures."""
        self.simulator = GithubSimulator()
        self.simulator.initialize()
        self.tool = GithubTool(self.simulator)

    def test_tool_properties(self):
        """Test tool properties."""
        self.assertEqual(self.tool.name, "github")
        self.assertIn("GitHub CI/CD", self.tool.description)

    def test_tool_input_schema(self):
        """Test tool input schema."""
        schema = self.tool.input_schema
        self.assertEqual(schema.type, "object")
        self.assertIn("operation", schema.required)

    def test_execute_list_workflow_runs(self):
        """Test executing list_workflow_runs operation."""
        result = self.tool.execute({
            "operation": "list_workflow_runs",
            "repo": "repocli/test-ci",
            "branch": "main"
        })

        self.assertTrue(result["success"])
        self.assertIn("data", result)

    def test_execute_inspect_commit(self):
        """Test executing inspect_commit operation."""
        result = self.tool.execute({
            "operation": "inspect_commit",
            "repo": "repocli/test-ci",
            "sha": "aaa111"
        })

        self.assertTrue(result["success"])
        self.assertIn("sha", result["data"])

    def test_execute_invalid_operation(self):
        """Test executing invalid operation."""
        result = self.tool.execute({
            "operation": "invalid_operation"
        })

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_execute_missing_parameters(self):
        """Test executing with missing parameters."""
        result = self.tool.execute({
            "operation": "inspect_commit"
        })

        self.assertFalse(result["success"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
