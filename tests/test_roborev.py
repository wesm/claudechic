"""Tests for roborev integration - models and CLI parsing."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from claudechic.features.roborev.models import ReviewJob, ReviewDetail
from claudechic.features.roborev.cli import list_reviews, show_review
from claudechic.widgets.layout.reviews import ReviewItem


# =============================================================================
# ReviewJob.from_dict
# =============================================================================


class TestReviewJobFromDict:
    def test_normal_data(self):
        job = ReviewJob.from_dict(
            {
                "id": 42,
                "git_ref": "abc1234def",
                "branch": "main",
                "agent": "codex",
                "status": "done",
                "verdict": "pass",
                "addressed": False,
                "commit_subject": "Fix bug",
            }
        )
        assert job.id == "42"
        assert job.git_ref == "abc1234def"
        assert job.branch == "main"
        assert job.verdict == "pass"
        assert job.addressed is False
        assert job.commit_subject == "Fix bug"

    def test_null_fields(self):
        """Null JSON values should become empty strings, not 'None'."""
        job = ReviewJob.from_dict(
            {
                "id": None,
                "git_ref": None,
                "verdict": None,
                "commit_subject": None,
            }
        )
        assert job.id == ""
        assert job.git_ref == ""
        assert job.verdict == ""
        assert job.commit_subject == ""

    def test_missing_fields(self):
        """Missing keys should use defaults."""
        job = ReviewJob.from_dict({"id": 1})
        assert job.id == "1"
        assert job.git_ref == ""
        assert job.verdict == ""
        assert job.addressed is False

    def test_string_id(self):
        """String IDs should pass through."""
        job = ReviewJob.from_dict({"id": "abc-123"})
        assert job.id == "abc-123"


# =============================================================================
# ReviewDetail.from_dict
# =============================================================================


class TestReviewDetailFromDict:
    def test_with_nested_job(self):
        detail = ReviewDetail.from_dict(
            {
                "id": 99,
                "job_id": 42,
                "agent": "codex",
                "output": "Looks good",
                "addressed": True,
                "job": {
                    "id": 42,
                    "branch": "main",
                    "verdict": "pass",
                },
            }
        )
        assert detail.id == "99"
        assert detail.job_id == "42"
        assert detail.output == "Looks good"
        assert detail.addressed is True
        assert detail.job is not None
        assert detail.job.branch == "main"

    def test_null_job(self):
        detail = ReviewDetail.from_dict(
            {
                "id": 1,
                "job": None,
            }
        )
        assert detail.job is None

    def test_null_ids(self):
        detail = ReviewDetail.from_dict(
            {
                "id": None,
                "job_id": None,
            }
        )
        assert detail.id == ""
        assert detail.job_id == ""


# =============================================================================
# list_reviews CLI parsing
# =============================================================================


class TestListReviews:
    def test_bare_array(self, tmp_path):
        """Parses a bare JSON array from roborev list --json."""
        payload = json.dumps(
            [
                {"id": 1, "branch": "main", "status": "done", "verdict": "pass"},
                {"id": 2, "branch": "main", "status": "running"},
            ]
        )
        mock_result = MagicMock(returncode=0, stdout=payload, stderr="")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            reviews = list_reviews(tmp_path, branch="main")
        assert len(reviews) == 2
        assert reviews[0].id == "1"
        assert reviews[0].verdict == "pass"
        assert reviews[1].status == "running"

    def test_empty_array(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="[]", stderr="")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            reviews = list_reviews(tmp_path)
        assert reviews == []

    def test_roborev_not_available(self, tmp_path):
        with patch(
            "claudechic.features.roborev.cli.is_roborev_available", return_value=False
        ):
            reviews = list_reviews(tmp_path)
        assert reviews == []

    def test_invalid_json(self, tmp_path):
        mock_result = MagicMock(returncode=0, stdout="not json", stderr="")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            reviews = list_reviews(tmp_path)
        assert reviews == []

    def test_filters_addressed(self, tmp_path):
        """Only unaddressed reviews are returned."""
        payload = json.dumps(
            [
                {"id": 1, "status": "done", "verdict": "F", "addressed": False},
                {"id": 2, "status": "done", "verdict": "P", "addressed": True},
                {"id": 3, "status": "running", "addressed": False},
            ]
        )
        mock_result = MagicMock(returncode=0, stdout=payload, stderr="")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            reviews = list_reviews(tmp_path)
        assert len(reviews) == 2
        assert reviews[0].id == "1"
        assert reviews[1].id == "3"

    def test_limit_applied_after_filter(self, tmp_path):
        """Limit is applied after filtering out addressed reviews."""
        payload = json.dumps(
            [{"id": i, "status": "done", "addressed": False} for i in range(10)]
            + [
                {"id": 100, "status": "done", "addressed": True},
            ]
        )
        mock_result = MagicMock(returncode=0, stdout=payload, stderr="")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            reviews = list_reviews(tmp_path, limit=5)
        assert len(reviews) == 5
        assert reviews[0].id == "0"
        assert reviews[4].id == "4"

    def test_nonzero_exit(self, tmp_path):
        mock_result = MagicMock(returncode=1, stdout="", stderr="error")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            reviews = list_reviews(tmp_path)
        assert reviews == []


# =============================================================================
# show_review CLI parsing
# =============================================================================


class TestShowReview:
    def test_returns_detail(self, tmp_path):
        payload = json.dumps(
            {
                "id": 99,
                "job_id": 42,
                "agent": "codex",
                "output": "No issues found.",
                "job": {"id": 42, "verdict": "pass", "branch": "main"},
            }
        )
        mock_result = MagicMock(returncode=0, stdout=payload, stderr="")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            detail = show_review("42", tmp_path)
        assert detail is not None
        assert detail.id == "99"
        assert detail.job is not None
        assert detail.job.verdict == "pass"

    def test_not_found(self, tmp_path):
        mock_result = MagicMock(returncode=1, stdout="", stderr="not found")
        with (
            patch(
                "claudechic.features.roborev.cli.is_roborev_available",
                return_value=True,
            ),
            patch("subprocess.run", return_value=mock_result),
        ):
            detail = show_review("999", tmp_path)
        assert detail is None


# =============================================================================
# ReviewItem rendering
# =============================================================================


def _make_item(verdict: str = "", status: str = "done", **kwargs) -> ReviewItem:
    """Create a ReviewItem without mounting it."""
    data = {
        "id": 1,
        "git_ref": "abc1234",
        "commit_subject": "test",
        "status": status,
        "verdict": verdict,
        **kwargs,
    }
    return ReviewItem(ReviewJob.from_dict(data))


class TestReviewItemRender:
    def test_pass_long(self):
        text = _make_item(verdict="pass").render()
        assert text.plain.startswith("P ")

    def test_pass_short(self):
        text = _make_item(verdict="P").render()
        assert text.plain.startswith("P ")

    def test_fail_long(self):
        text = _make_item(verdict="fail").render()
        assert text.plain.startswith("F ")

    def test_fail_short(self):
        text = _make_item(verdict="F").render()
        assert text.plain.startswith("F ")

    def test_unknown_verdict(self):
        text = _make_item(verdict="").render()
        assert text.plain.startswith("? ")

    def test_running_shows_spinner(self):
        """Running status shows a spinner frame, not a verdict."""
        item = _make_item(verdict="", status="running")
        text = item.render()
        from claudechic.widgets.layout.reviews import _SPINNER_FRAMES

        assert text.plain[0] in _SPINNER_FRAMES

    def test_queued_shows_spinner(self):
        item = _make_item(verdict="", status="queued")
        text = item.render()
        from claudechic.widgets.layout.reviews import _SPINNER_FRAMES

        assert text.plain[0] in _SPINNER_FRAMES
