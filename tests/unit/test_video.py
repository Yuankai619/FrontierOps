from datetime import datetime, timezone
import json
import re
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import wave

from frontierops.adapters.video import (
    HeyGenNarrator, HyperFramesPreviewRenderer, NarrationAudio, TimedWord,
    infer_tts_language,
)
from frontierops.application.render import claim_fingerprints
from frontierops.domain.models import BriefingSpec


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def briefing() -> BriefingSpec:
    claims = [
        {"text": text, "kind": "factual", "evidence_ids": ["e1"]}
        for text in ("Problem", "Idea", "Method", "Novelty", "Results", "Limits", "Impact")
    ]
    return BriefingSpec.model_validate({
        "artifact_id": "b1", "run_id": "r1", "created_at": NOW, "producer": "test",
        "title": "Research update", "language": "en", "target_duration_seconds": 60,
        "render_targets": ["video"], "sections": [{
            "id": "paper", "duration_seconds": 60, "headline": "Paper2Video",
            "claims": claims, "narration_script": "This paper explains research videos.",
        }],
    })


class VideoPreviewTests(unittest.TestCase):
    def test_composition_preserves_claims_audio_and_timed_captions(self) -> None:
        spec = briefing()
        words = [TimedWord("This", 0, .3), TimedWord("paper", .31, .7),
                 TimedWord("explains", .71, 1.2)]
        documents = HyperFramesPreviewRenderer().render(
            spec, NarrationAudio(words, 1.4), 1920, 1080
        )
        document = documents["index.html"]
        metadata = re.search(
            r'<script id="frontierops-claims" type="application/json">(.*?)</script>', document,
        )
        self.assertIsNotNone(metadata)
        self.assertEqual(json.loads(metadata.group(1))["claim_fingerprints"],
                         claim_fingerprints(spec))
        self.assertEqual("".join(documents.values()).count('data-claim-fingerprint="'), 7)
        self.assertIn('id="narration" src="narration.wav"', document)
        self.assertIn("data-no-timeline", document)
        self.assertIn('data-start="0.000" data-duration="1.200"', document)
        self.assertIn('data-duration="1.4"', document)
        self.assertEqual(len([path for path in documents if path.startswith("compositions/")]), 3)

    def test_language_inference_follows_the_script_not_briefing_locale(self) -> None:
        self.assertEqual(infer_tts_language("This is an English paper."), "en")
        self.assertEqual(infer_tts_language("這是一篇新的研究論文。"), "zh")

    def test_narrator_invokes_adapter_without_a_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = root / "heygen-tts.mjs"
            adapter.write_text("// fixture", encoding="utf-8")

            def run(command, **kwargs):
                audio_path = Path(command[command.index("--output") + 1])
                words_path = Path(command[command.index("--words") + 1])
                with wave.open(str(audio_path), "wb") as audio:
                    audio.setparams((1, 2, 8000, 4000, "NONE", "not compressed"))
                    audio.writeframes(b"\0\0" * 4000)
                words_path.write_text(
                    json.dumps([{"text": "Hello", "start": 0, "end": .4}]), encoding="utf-8"
                )
                return type("Completed", (), {"returncode": 0, "stderr": ""})()

            with patch("frontierops.adapters.video.subprocess.run", side_effect=run) as invoked:
                words = HeyGenNarrator(adapter, "voice-1").synthesize("Hello", root / "out", "en")
            self.assertEqual(words.words, [TimedWord("Hello", 0, .4)])
            self.assertEqual(words.duration, .5)
            command = invoked.call_args.args[0]
            self.assertEqual(command[:2], ["node", str(adapter)])
            self.assertNotIn("--lang", command)
            self.assertEqual(command[-2:], ["--voice", "voice-1"])


if __name__ == "__main__":
    unittest.main()
