"""Adapters for an auditable narrated HyperFrames preview project."""

from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import subprocess
import wave

from frontierops.application.render import claim_fingerprint, claim_fingerprints
from frontierops.domain.models import BriefingSpec


@dataclass(frozen=True)
class TimedWord:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class NarrationAudio:
    words: list[TimedWord]
    duration: float


class HeyGenNarrator:
    """Invoke the installed media-use adapter without owning HeyGen credentials."""

    def __init__(self, script_path: Path, voice_id: str | None = None) -> None:
        self.script_path = script_path
        self.voice_id = voice_id

    def synthesize(self, text: str, output_dir: Path, language: str) -> NarrationAudio:
        if not self.script_path.is_file():
            raise ValueError(f"HeyGen TTS adapter not found: {self.script_path}")
        output_dir.mkdir(parents=True, exist_ok=True)
        script = output_dir / "narration.txt"
        audio = output_dir / "narration.wav"
        timings = output_dir / "narration.words.json"
        if audio.is_file() and timings.is_file():
            return NarrationAudio(_load_words(timings), _wav_duration(audio))
        script.write_text(text.strip() + "\n", encoding="utf-8")
        command = [
            "node", str(self.script_path), str(script), "--output", str(audio),
            "--words", str(timings),
        ]
        if self.voice_id:
            command.extend(["--voice", self.voice_id])
        if language and language != "en":
            command.extend(["--lang", language])
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode:
            detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "unknown error"
            raise ValueError(f"HeyGen narration failed: {detail}")
        return NarrationAudio(_load_words(timings), _wav_duration(audio))


class HyperFramesPreviewRenderer:
    def render(
        self, briefing: BriefingSpec, narration: NarrationAudio, width: int, height: int
    ) -> dict[str, str]:
        if not narration.words:
            raise ValueError("HyperFrames preview requires word timestamps")
        duration = round(narration.duration, 3)
        scene_hosts, scene_files = _scenes(briefing, duration, width, height)
        captions = _captions(narration.words)
        metadata = json.dumps({
            "briefing_id": briefing.artifact_id,
            "claim_fingerprints": claim_fingerprints(briefing),
        }, ensure_ascii=False).replace("</", "<\\/")
        index = f"""<!doctype html>
<html lang="{escape(briefing.language)}"><head><meta charset="utf-8">
<meta name="viewport" content="width={width},height={height}"><title>{escape(briefing.title)}</title>
<style>
:root{{--bg:#101712;--panel:#1a251e;--ink:#f1eee4;--muted:#aeb8b0;--accent:#e37459}}
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:var(--bg);color:var(--ink);font-family:Arial,sans-serif}}
#root{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:radial-gradient(circle at 82% 12%,#2c4230 0,transparent 38%),var(--bg)}}
.clip{{position:absolute;inset:0}}.scene{{padding:72px 92px 190px;display:grid;grid-template-rows:auto 1fr;gap:44px}}
.topline{{display:flex;justify-content:space-between;color:var(--accent);font-size:22px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}
h1{{max-width:1500px;margin:0;font:700 72px/1.05 Georgia,serif}}.claims{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}}
.claim{{padding:28px 32px;border:2px solid #405146;background:rgba(26,37,30,.92)}}.claim h2{{margin:0 0 12px;color:var(--accent);font-size:21px;text-transform:uppercase}}
.claim p{{margin:0;font-size:28px;line-height:1.28}}.caption{{inset:auto 90px 48px;min-height:92px;padding:22px 34px;border-radius:12px;background:rgba(3,7,5,.92);font-size:34px;line-height:1.35;text-align:center;z-index:20}}
.mark{{position:absolute;right:92px;bottom:210px;color:var(--muted);font-size:18px}}
</style></head><body>
<main id="root" data-composition-id="frontier-briefing" data-no-timeline data-start="0" data-width="{width}" data-height="{height}" data-duration="{duration}">
{''.join(scene_hosts)}{''.join(captions)}
<audio id="narration" src="narration.wav" data-start="0" data-duration="{duration}" data-track-index="20" data-volume="1"></audio>
</main>
<script id="frontierops-claims" type="application/json">{metadata}</script>
</body></html>"""
        return {"index.html": index, **scene_files}


def infer_tts_language(text: str) -> str:
    visible = [character for character in text if not character.isspace()]
    if not visible:
        return "en"
    cjk = sum("\u3400" <= character <= "\u9fff" for character in visible)
    return "zh" if cjk / len(visible) >= 0.1 else "en"


def _load_words(path: Path) -> list[TimedWord]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    words = [TimedWord(str(item["text"]), float(item["start"]), float(item["end"])) for item in raw]
    if any(word.start < 0 or word.end <= word.start for word in words):
        raise ValueError("HeyGen returned invalid word timestamps")
    if any(current.start < previous.start for previous, current in zip(words, words[1:])):
        raise ValueError("HeyGen returned non-monotonic word timestamps")
    return words


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as source:
        return source.getnframes() / source.getframerate()


def _scenes(
    briefing: BriefingSpec, duration: float, width: int, height: int
) -> tuple[list[str], dict[str, str]]:
    weights = [max(1, len(section.narration_script.split())) for section in briefing.sections]
    total = sum(weights)
    cursor = 0.0
    hosts: list[str] = []
    files: dict[str, str] = {}
    labels = ["Problem", "Core idea", "Method", "Novelty", "Experiments", "Limitations", "Why it matters"]
    groups = [(0, 1, 6), (2, 3), (4, 5)]
    for section, weight in zip(briefing.sections, weights):
        section_duration = duration * weight / total
        scene_duration = section_duration / len(groups)
        for part, indices in enumerate(groups, 1):
            start = cursor + scene_duration * (part - 1)
            claims = "".join(
                f'<article class="claim" data-claim-fingerprint="{claim_fingerprint(section.claims[index])}">'
                f'<h2>{labels[index]}</h2><p>{escape(section.claims[index].text)}</p></article>'
                for index in indices if index < len(section.claims)
            )
            scene_id = f"scene-{section.id}-{part}"
            path = f"compositions/{scene_id}.html"
            hosts.append(
                f'<div id="slot-{escape(scene_id)}" class="clip" data-composition-id="{escape(scene_id)}" '
                f'data-composition-src="{escape(path)}" data-start="{start:.3f}" '
                f'data-duration="{scene_duration:.3f}" data-track-index="{part}" '
                f'data-width="{width}" data-height="{height}"></div>'
            )
            files[path] = _scene_document(
                scene_id, section.headline, part, claims, scene_duration, width, height
            )
        cursor += section_duration
    return hosts, files


def _scene_document(
    scene_id: str, headline: str, part: int, claims: str,
    duration: float, width: int, height: int,
) -> str:
    return f"""<!doctype html><html><body><template><style>
#root{{position:absolute;inset:0;box-sizing:border-box;padding:72px 92px 190px;display:grid;grid-template-rows:auto 1fr;gap:44px;background:radial-gradient(circle at 82% 12%,#2c4230 0,transparent 38%),#101712;color:#f1eee4;font-family:Arial,sans-serif;overflow:hidden}}
.topline{{display:flex;justify-content:space-between;color:#e37459;font-size:22px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}
h1{{max-width:1500px;margin:0;font:700 72px/1.05 Georgia,serif}}.claims{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}}
.claim{{box-sizing:border-box;padding:28px 32px;border:2px solid #405146;background:rgba(26,37,30,.92)}}.claim h2{{margin:0 0 12px;color:#e37459;font-size:21px;text-transform:uppercase}}
.claim p{{margin:0;font-size:28px;line-height:1.28}}.mark{{position:absolute;right:92px;bottom:210px;color:#aeb8b0;font-size:18px}}
</style><section id="root" data-composition-id="{escape(scene_id)}" data-no-timeline data-width="{width}" data-height="{height}" data-duration="{duration:.3f}">
<header><div class="topline"><span>FrontierOps · approved evidence</span><span>{part}/3</span></div><h1>{escape(headline)}</h1></header>
<div class="claims">{claims}</div><span class="mark">Research frontier briefing</span></section>
</template></body></html>"""


def _captions(words: list[TimedWord], size: int = 9) -> list[str]:
    result = []
    for index in range(0, len(words), size):
        chunk = words[index:index + size]
        start, end = chunk[0].start, chunk[-1].end
        text = " ".join(word.text for word in chunk)
        result.append(
            f'<div id="caption-{index // size}" class="clip caption" data-layout-allow-caption-zone '
            f'data-start="{start:.3f}" data-duration="{end - start:.3f}" data-track-index="10">'
            f'{escape(text)}</div>'
        )
    return result
