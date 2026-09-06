"""Deterministic GitHub CI simulator for Syndicate."""

from typing import Any, Dict, List
from datetime import datetime

from ..models.task import ToolInputSchema, ToolResult, ToolCall
from ..models.tool import Tool, Tool as AbstractTool


class GithubSimulator:
    """
    Deterministic GitHub CI simulator for testing and development.

    This simulator provides a small deterministic dataset representing
    several CI failure scenarios with known ground truth.
    """

    def __init__(self):
        """Initialize the simulator with deterministic scenarios."""
        self._scenarios = self._initialize_scenarios()
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Check if simulator has been initialized."""
        return self._initialized

    def initialize(self):
        """Initialize the simulator with scenarios."""
        if not self._initialized:
            self._initialized = True

    def _initialize_scenarios(self) -> Dict[str, Any]:
        """Initialize deterministic CI failure scenarios."""
        return {
            "repocli/test-ci": {
                "workflows": {
                    "test.yml": {
                        "runs": [
                            {
                                "id": 1,
                                "name": "Test Run #1",
                                "branch": "main",
                                "status": "success",
                                "commit": "abc123def456",
                                "conclusion": "success",
                                "triggered_at": "2024-01-15T10:00:00Z",
                                "jobs": {
                                    "test": {
                                        "status": "completed",
                                        "conclusion": "success",
                                        "run_id": 1,
                                    }
                                },
                            },
                            {
                                "id": 2,
                                "name": "Test Run #2",
                                "branch": "main",
                                "status": "success",
                                "commit": "def456ghi789",
                                "conclusion": "success",
                                "triggered_at": "2024-01-15T11:00:00Z",
                                "jobs": {
                                    "test": {
                                        "status": "completed",
                                        "conclusion": "failure",
                                        "run_id": 2,
                                    },
                                    "lint": {
                                        "status": "completed",
                                        "conclusion": "success",
                                        "run_id": 2,
                                    },
                                },
                            },
                            {
                                "id": 3,
                                "name": "Test Run #3",
                                "branch": "main",
                                "status": "in_progress",
                                "commit": "ghi789jkl012",
                                "triggered_at": "2024-01-15T12:00:00Z",
                            },
                        ]
                    }
                },
                "commits": {
                    "abc123def456": {
                        "sha": "abc123def456",
                        "message": "Initial commit",
                        "author": "alice",
                        "timestamp": "2024-01-15T10:00:00Z",
                        "branch": "main",
                    },
                    "def456ghi789": {
                        "sha": "def456ghi789",
                        "message": "Fix critical bug",
                        "author": "bob",
                        "timestamp": "2024-01-15T11:00:00Z",
                        "branch": "main",
                        "files_changed": [
                            {"path": "src/test.py", "changes": 5, "additions": 5, "deletions": 0},
                        ],
                    },
                    "ghi789jkl012": {
                        "sha": "ghi789jkl012",
                        "message": "Work in progress",
                        "author": "alice",
                        "timestamp": "2024-01-15T12:00:00Z",
                        "branch": "main",
                        "files_changed": [
                            {"path": "src/deploy.py", "changes": 10, "additions": 10, "deletions": 0},
                        ],
                    },
                },
                "pull_requests": {
                    123: {
                        "id": 123,
                        "title": "Feature: Add new authentication",
                        "head": "alice:auth-feature",
                        "base": "alice:main",
                        "state": "open",
                        "created_at": "2024-01-14T10:00:00Z",
                        "closed_at": None,
                        "commits": [
                            {
                                "sha": "def456ghi789",
                                "author": "bob",
                            }
                        ],
                        "reviews": [],
                        "check_runs": [],
                    }
                },
                "issues": {
                    100: {
                        "id": 100,
                        "title": "CI pipeline failing in production",
                        "state": "open",
                        "created_at": "2024-01-13T15:00:00Z",
                        "updated_at": "2024-01-15T11:30:00Z",
                        "labels": ["bug", "ci"],
                        "author": "charlie",
                        "body": "The test job is failing consistently after deployment.",
                    },
                    101: {
                        "id": 101,
                        "title": "Documentation update needed",
                        "state": "open",
                        "created_at": "2024-01-15T08:00:00Z",
                        "updated_at": "2024-01-15T09:00:00Z",
                        "labels": ["enhancement"],
                        "author": "dave",
                        "body": "README needs updates for new features.",
                    },
                },
            },
            "repocli/integration-test": {
                "workflows": {
                    "integration.yml": {
                        "runs": [
                            {
                                "id": 1,
                                "name": "Integration Test #1",
                                "branch": "main",
                                "status": "success",
                                "commit": "aaa111",
                                "conclusion": "success",
                                "triggered_at": "2024-01-14T09:00:00Z",
                                "jobs": {
                                    "test": {
                                        "status": "completed",
                                        "conclusion": "success",
                                        "run_id": 1,
                                    }
                                },
                            },
                            {
                                "id": 2,
                                "name": "Integration Test #2",
                                "branch": "main",
                                "status": "success",
                                "commit": "bbb222",
                                "conclusion": "cancelled",
                                "triggered_at": "2024-01-14T10:00:00Z",
                                "jobs": {
                                    "test": {
                                        "status": "in_progress",
                                        "conclusion": "cancelled",
                                        "run_id": 2,
                                    }
                                },
                            },
                        ]
                    }
                },
                "commits": {
                    "aaa111": {
                        "sha": "aaa111",
                        "message": "Add integration tests",
                        "author": "eve",
                        "timestamp": "2024-01-14T09:00:00Z",
                        "branch": "main",
                    },
                    "bbb222": {
                        "sha": "bbb222",
                        "message": "Temporarily disable test",
                        "author": "eve",
                        "timestamp": "2024-01-14T10:00:00Z",
                        "branch": "main",
                    },
                },
                "issues": {
                    200: {
                        "id": 200,
                        "title": "Integration tests timing out",
                        "state": "open",
                        "created_at": "2024-01-15T10:00:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "labels": ["bug", "integration"],
                        "author": "frank",
                        "body": "Tests are taking too long and timing out.",
                    }
                },
            },
        }

    def _get_repo_data(self, repo: str) -> Dict[str, Any]:
        """Get repository data from scenarios or return empty structure."""
        repo = repo.lower()
        if repo in self._scenarios:
            return self._scenarios[repo]
        return {}

    def search_repository(self, query: str, repo: str) -> List[Dict[str, Any]]:
        """
        Search repository for matching commits, issues, or PRs.

        Args:
            query: Search query (commit message, issue title, PR title, etc.)
            repo: Repository name

        Returns:
            List of matching items (issues first, then PRs, then commits).
        """
        repo_data = self._get_repo_data(repo)
        results = []
        query = query.lower()

        # Search issues first (match title or labels)
        for issue_id, issue in repo_data.get("issues", {}).items():
            labels_lower = [l.lower() for l in issue.get("labels", [])]
            if query in issue["title"].lower() or query in labels_lower:
                results.append(
                    {
                        "type": "issue",
                        "id": issue_id,
                        "title": issue["title"],
                        "state": issue["state"],
                        "labels": issue["labels"],
                        "author": issue["author"],
                    }
                )

        # Search PRs
        for pr_id, pr in repo_data.get("pull_requests", {}).items():
            if query in pr["title"].lower():
                results.append(
                    {
                        "type": "pull_request",
                        "id": pr_id,
                        "title": pr["title"],
                        "state": pr["state"],
                        "head": pr["head"],
                        "base": pr["base"],
                    }
                )

        # Search commits
        for sha, commit in repo_data.get("commits", {}).items():
            if query in commit["message"].lower():
                results.append(
                    {
                        "type": "commit",
                        "sha": sha,
                        "message": commit["message"],
                        "author": commit["author"],
                        "timestamp": commit["timestamp"],
                    }
                )

        return results

    def list_workflow_runs(
        self, repo: str, branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """
        List workflow runs for a repository and branch.

        Args:
            repo: Repository name
            branch: Branch name (default: "main")

        Returns:
            List of workflow runs.
        """
        repo_data = self._get_repo_data(repo)
        workflows = repo_data.get("workflows", {})
        results = []

        for workflow_name, workflow_data in workflows.items():
            for run in workflow_data.get("runs", []):
                if run.get("branch") == branch:
                    run_data = {
                        "id": run["id"],
                        "name": run["name"],
                        "branch": run["branch"],
                        "status": run["status"],
                        "conclusion": run.get("conclusion", None),
                        "commit": run.get("commit", None),
                        "triggered_at": run["triggered_at"],
                    }
                    results.append(run_data)

        return results

    def inspect_workflow_run(self, repo: str, run_id: int) -> Dict[str, Any]:
        """
        Inspect a specific workflow run.

        Args:
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            Workflow run details including jobs.
        """
        repo_data = self._get_repo_data(repo)
        workflows = repo_data.get("workflows", {})

        for workflow_name, workflow_data in workflows.items():
            for run in workflow_data.get("runs", []):
                if run["id"] == run_id:
                    return {
                        "id": run["id"],
                        "name": run["name"],
                        "branch": run["branch"],
                        "status": run["status"],
                        "conclusion": run.get("conclusion", None),
                        "sha": run.get("commit", None),
                        "triggered_at": run["triggered_at"],
                        "jobs": run.get("jobs", {}),
                    }

        return {"error": f"Workflow run {run_id} not found in repository {repo}"}

    def inspect_job_logs(self, repo: str, run_id: int, job_name: str) -> str:
        """
        Inspect job logs for a specific workflow run and job.

        Args:
            repo: Repository name
            run_id: Workflow run ID
            job_name: Job name

        Returns:
            Job log content.
        """
        run_data = self.inspect_workflow_run(repo, run_id)

        if "error" in run_data:
            return f"Error: {run_data['error']}"

        jobs = run_data.get("jobs", {})
        if job_name not in jobs:
            return f"Job '{job_name}' not found in workflow run {run_id}"

        job = jobs[job_name]
        status = job.get("conclusion", "in_progress")

        logs = f"""Job: {job_name}
Status: {status}
Run ID: {run_id}

"""
        if status == "failure":
            logs += """ERROR: Test failed
Error message: Assertion failed
Failed tests: test_login, test_register
Duration: 2.5s

"""
        elif status == "success":
            logs += """INFO: All tests passed
Duration: 3.2s
Coverage: 87%

"""
        else:
            logs += """INFO: Job in progress...

"""
        return logs

    def inspect_commit(self, repo: str, sha: str) -> Dict[str, Any]:
        """
        Inspect a specific commit.

        Args:
            repo: Repository name
            sha: Commit SHA

        Returns:
            Commit details.
        """
        repo_data = self._get_repo_data(repo)
        commits = repo_data.get("commits", {})

        if sha in commits:
            commit = commits[sha]
            return {
                "sha": commit["sha"],
                "message": commit["message"],
                "author": commit["author"],
                "timestamp": commit["timestamp"],
                "branch": commit["branch"],
                "files_changed": commit.get("files_changed", []),
            }

        # Fallback: search other repositories for the commit SHA
        for other_repo, other_data in self._scenarios.items():
            if other_repo.lower() == repo.lower():
                continue
            other_commits = other_data.get("commits", {})
            if sha in other_commits:
                commit = other_commits[sha]
                return {
                    "sha": commit["sha"],
                    "message": commit["message"],
                    "author": commit["author"],
                    "timestamp": commit["timestamp"],
                    "branch": commit["branch"],
                    "files_changed": commit.get("files_changed", []),
                }

        return {"error": f"Commit {sha} not found in repository {repo}"}

    def inspect_pull_request(self, repo: str, pr_id: int) -> Dict[str, Any]:
        """
        Inspect a specific pull request.

        Args:
            repo: Repository name
            pr_id: Pull request ID

        Returns:
            PR details.
        """
        repo_data = self._get_repo_data(repo)
        prs = repo_data.get("pull_requests", {})

        if pr_id not in prs:
            return {"error": f"Pull request {pr_id} not found in repository {repo}"}

        pr = prs[pr_id]
        return {
            "id": pr["id"],
            "title": pr["title"],
            "state": pr["state"],
            "head": pr["head"],
            "base": pr["base"],
            "created_at": pr["created_at"],
            "closed_at": pr["closed_at"],
            "commits": pr["commits"],
            "reviews": pr["reviews"],
            "check_runs": pr["check_runs"],
        }

    def inspect_issue(self, repo: str, issue_id: int) -> Dict[str, Any]:
        """
        Inspect a specific issue.

        Args:
            repo: Repository name
            issue_id: Issue ID

        Returns:
            Issue details.
        """
        repo_data = self._get_repo_data(repo)
        issues = repo_data.get("issues", {})

        if issue_id not in issues:
            return {"error": f"Issue {issue_id} not found in repository {repo}"}

        issue = issues[issue_id]
        return {
            "id": issue["id"],
            "title": issue["title"],
            "state": issue["state"],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "labels": issue["labels"],
            "author": issue["author"],
            "body": issue["body"],
        }


class GithubTool(AbstractTool):
    """GitHub CI tool implementations using the simulator."""

    def __init__(self, simulator: GithubSimulator):
        """
        Initialize GitHub tool with simulator.

        Args:
            simulator: GithubSimulator instance.
        """
        self._simulator = simulator

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "GitHub CI/CD tools for repository inspection"

    @property
    def input_schema(self) -> ToolInputSchema:
        return ToolInputSchema(
            type="object",
            description="Input schema varies by operation",
            required=["operation"],
            properties={
                "operation": {
                    "type": "string",
                    "enum": [
                        "list_workflow_runs",
                        "inspect_workflow_run",
                        "inspect_job_logs",
                        "inspect_commit",
                        "inspect_pull_request",
                        "inspect_issue",
                        "search_repository",
                    ],
                    "description": "Operation to perform",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name",
                    "default": "main",
                },
                "run_id": {
                    "type": "integer",
                    "description": "Workflow run ID",
                },
                "job_name": {
                    "type": "string",
                    "description": "Job name",
                },
                "sha": {
                    "type": "string",
                    "description": "Commit SHA",
                },
                "pr_id": {
                    "type": "integer",
                    "description": "Pull request ID",
                },
                "issue_id": {
                    "type": "integer",
                    "description": "Issue ID",
                },
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
        )

    def execute(self, input_data: dict) -> dict:
        """
        Execute the GitHub tool.

        Args:
            input_data: Dictionary containing operation and parameters.

        Returns:
            Dictionary containing tool output and status.
        """
        operation = input_data.get("operation")
        if not operation:
            return {"success": False, "error": "Operation not specified"}

        if operation == "list_workflow_runs":
            repo = input_data.get("repo")
            branch = input_data.get("branch", "main")
            if not repo:
                return {"success": False, "error": "Repository not specified"}
            runs = self._simulator.list_workflow_runs(repo, branch)
            return {
                "operation": operation,
                "success": True,
                "data": runs,
            }

        elif operation == "inspect_workflow_run":
            repo = input_data.get("repo")
            run_id = input_data.get("run_id")
            if not repo or run_id is None:
                return {"success": False, "error": "Repository and run_id are required"}
            result = self._simulator.inspect_workflow_run(repo, run_id)
            return {
                "operation": operation,
                "success": True,
                "data": result,
            }

        elif operation == "inspect_job_logs":
            repo = input_data.get("repo")
            run_id = input_data.get("run_id")
            job_name = input_data.get("job_name")
            if not repo or run_id is None or not job_name:
                return {"success": False, "error": "repo, run_id, and job_name are required"}
            logs = self._simulator.inspect_job_logs(repo, run_id, job_name)
            return {
                "operation": operation,
                "success": True,
                "data": logs,
            }

        elif operation == "inspect_commit":
            repo = input_data.get("repo")
            sha = input_data.get("sha")
            if not repo or not sha:
                return {"success": False, "error": "Repository and sha are required"}
            result = self._simulator.inspect_commit(repo, sha)
            return {
                "operation": operation,
                "success": True,
                "data": result,
            }

        elif operation == "inspect_pull_request":
            repo = input_data.get("repo")
            pr_id = input_data.get("pr_id")
            if not repo or pr_id is None:
                return {"success": False, "error": "Repository and pr_id are required"}
            result = self._simulator.inspect_pull_request(repo, pr_id)
            return {
                "operation": operation,
                "success": True,
                "data": result,
            }

        elif operation == "inspect_issue":
            repo = input_data.get("repo")
            issue_id = input_data.get("issue_id")
            if not repo or issue_id is None:
                return {"success": False, "error": "Repository and issue_id are required"}
            result = self._simulator.inspect_issue(repo, issue_id)
            return {
                "operation": operation,
                "success": True,
                "data": result,
            }

        elif operation == "search_repository":
            repo = input_data.get("repo")
            query = input_data.get("query")
            if not repo or not query:
                return {"success": False, "error": "Repository and query are required"}
            results = self._simulator.search_repository(query, repo)
            return {
                "operation": operation,
                "success": True,
                "data": results,
            }

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
