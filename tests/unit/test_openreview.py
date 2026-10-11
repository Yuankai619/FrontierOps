import unittest

from frontierops.adapters.openreview import OpenReviewProvider
from frontierops.domain.models import OpenReviewSourceConfig


class FakeGroup:
    content = {"submission_name": {"value": "Submission"}}


class FakeNote:
    def to_json(self) -> dict:
        return {
            "id": "note-1",
            "forum": "forum-1",
            "cdate": 1760000000000,
            "mdate": 1760000001000,
            "invitations": ["ICLR.cc/2026/Conference/-/Submission"],
            "content": {
                "title": {"value": "Research Agent"},
                "abstract": {"value": "Evidence-grounded agent."},
                "authors": {"value": ["Ada"]},
            },
            "details": {"replies": [{
                "id": "decision-1",
                "invitations": ["ICLR.cc/2026/Conference/Submission1/-/Decision"],
                "content": {"decision": {"value": "Accept"}},
            }]},
        }


class FakeClient:
    def __init__(self) -> None:
        self.params = {}

    def get_group(self, group_id: str) -> FakeGroup:
        self.group_id = group_id
        return FakeGroup()

    def get_all_notes(self, **params) -> list[FakeNote]:
        self.params = params
        return [FakeNote()]


class OpenReviewProviderTests(unittest.TestCase):
    def test_preserves_forum_decision_and_reply_provenance(self) -> None:
        client = FakeClient()
        provider = OpenReviewProvider(
            OpenReviewSourceConfig(enabled=True, mode="live"),
            {"ICLR.cc/2026/Conference": ["Accept"]},
            client,
        )
        record = provider.fetch({}).records[0]
        self.assertEqual(record.external_id, "forum-1")
        self.assertEqual(record.payload["decision"], "Accept")
        self.assertEqual(record.payload["replies"][0]["id"], "decision-1")
        self.assertEqual(client.params["details"], "replies")
        self.assertIn("/-/Submission", client.params["invitation"])
