"""Adapters for an auditable narrated HyperFrames preview project."""

from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import subprocess
import textwrap
import wave

from frontierops.application.render import claim_fingerprint, claim_fingerprints
from frontierops.domain.models import BriefingSpec, Evidence


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
    def __init__(self, visuals: dict[str, dict] | None = None) -> None:
        self.visuals = visuals or {}

    def render(
        self, briefing: BriefingSpec, narration: NarrationAudio, width: int, height: int,
        evidence: list[Evidence] | None = None,
    ) -> dict[str, str]:
        if not narration.words:
            raise ValueError("HyperFrames preview requires word timestamps")
        duration = round(narration.duration, 3)
        scene_hosts, scene_files = _scenes(
            briefing, duration, width, height, self.visuals, evidence or []
        )
        captions = _captions(narration.words)
        metadata = json.dumps({
            "briefing_id": briefing.artifact_id,
            "claim_fingerprints": claim_fingerprints(briefing),
        }, ensure_ascii=False).replace("</", "<\\/")
        index = f"""<!doctype html>
<html lang="{escape(briefing.language)}"><head><meta charset="utf-8">
<meta name="viewport" content="width={width},height={height}"><title>{escape(briefing.title)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
:root{{--paper:#f8f7f3;--ink:#202722;--accent:#216b59}}
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:var(--paper);color:var(--ink);font-family:Arial,sans-serif}}
#root{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:var(--paper)}}
.clip{{position:absolute;inset:0}}.caption{{inset:auto 80px 42px;min-height:100px;padding:18px 28px;border-top:3px solid var(--accent);background:rgba(248,247,243,.96);font-size:34px;line-height:1.35;text-align:center;z-index:20}}
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
    briefing: BriefingSpec, duration: float, width: int, height: int,
    visuals: dict[str, dict], evidence: list[Evidence],
) -> tuple[list[str], dict[str, str]]:
    weights = [max(1, len(section.narration_script.split())) for section in briefing.sections]
    total = sum(weights)
    cursor = 0.0
    hosts: list[str] = []
    files: dict[str, str] = {}
    by_id = {item.artifact_id: item for item in evidence}
    for section, weight in zip(briefing.sections, weights):
        section_duration = duration * weight / total
        scene_duration = section_duration / 3
        for part in range(1, 4):
            start = cursor + scene_duration * (part - 1)
            scene_id = f"scene-{section.id}-{part}"
            path = f"compositions/{scene_id}.html"
            hosts.append(
                f'<div id="slot-{escape(scene_id)}" class="clip" data-composition-id="{escape(scene_id)}" '
                f'data-composition-src="{escape(path)}" data-start="{start:.3f}" '
                f'data-duration="{scene_duration:.3f}" data-track-index="{part}" '
                f'data-width="{width}" data-height="{height}"></div>'
            )
            files[path] = _scene_document(
                scene_id, section, part, scene_duration, width, height,
                visuals.get(section.id), by_id,
            )
        cursor += section_duration
    return hosts, files


def _scene_document(
    scene_id: str, section, part: int, duration: float, width: int, height: int,
    visual: dict | None, evidence: dict[str, Evidence],
) -> str:
    claims = section.claims
    if part == 1:
        headline = _short(claims[0].text.split(":", 1)[0] if claims else section.headline, 120)
        detail = claims[0].text.split(":", 1)[-1].strip() if claims else ""
        body = (f'<div class="context-grid focus">{_claim(claims, 0, "problem", detail)}'
                f'<div class="intro-side">{_claim(claims, 1, "idea")}'
                f'{_claim(claims, 3, "novelty")}</div></div>')
        source = _claim_source(claims, 0, evidence)
    elif part == 2:
        idea = claims[1].text if len(claims) > 1 else section.headline
        headline = _short(idea.split(" and ", 1)[0], 90)
        if visual:
            figure = (f'<figure class="source-figure"><img src="../assets/{escape(str(visual["uri"]).split("/")[-1], quote=True)}" '
                      f'alt="{escape(str(visual["label"]), quote=True)} from original paper">'
                      f'<figcaption>{escape(str(visual["label"]))} · p. {visual["page"]}</figcaption></figure>')
            source = f'{visual["label"]} · p. {visual["page"]}'
        else:
            figure = '<p class="figure-missing">No verified figure available for this paper.</p>'
            source = _claim_source(claims, 2, evidence)
        body = (f'<div class="method-body focus">{figure}<div class="method-notes">'
                f'{_claim(claims, 2, "method-note")}</div></div>')
    else:
        headline = _short(claims[4].text if len(claims) > 4 else section.headline, 135)
        impact = _claim(claims, 6, "impact-note") if len(claims) > 6 and claims[6].text != claims[4].text else ""
        body = (f'<div class="results-body focus">{_claim(claims, 4, "result-note")}'
                f'{_claim(claims, 5, "limit-note")}{impact}</div>')
        source = _claim_source(claims, 4, evidence)
    timeline = json.dumps(scene_id)
    return f"""<!doctype html><html><body><template><style>
#root{{position:absolute;inset:0;box-sizing:border-box;padding:76px 104px 185px;background:#f8f7f3;color:#202722;font-family:Arial,sans-serif;overflow:hidden}}
.headline{{max-width:1650px;margin:0 0 34px;font:700 67px/1.1 Georgia,serif}}
.context-grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:74px;margin-top:58px;align-items:start}}
.context-grid p{{margin:0;font:38px/1.35 Georgia,serif}}.intro-side{{border-top:5px solid #216b59;padding-top:24px;color:#216b59}}
.intro-side p{{font-size:32px;margin-bottom:30px}}.intro-side .novelty{{color:#4d5c51}}
.method-body{{display:grid;grid-template-rows:auto 1fr;gap:18px}}.source-figure{{margin:0}}.source-figure img{{display:block;width:100%;height:430px;object-fit:contain;background:#fff}}
.source-figure figcaption{{font-size:23px;color:#56645b;margin-top:8px}}.method-notes{{max-width:1500px;font-size:27px;line-height:1.3}}
.method-notes p{{margin:0}}.figure-missing{{padding:100px 0;font-size:36px;color:#5a665d}}
.results-body{{display:grid;grid-template-columns:1.25fr .75fr;gap:70px;margin-top:68px}}.results-body p{{margin:0;font:39px/1.38 Georgia,serif}}
.results-body .limit-note{{border-top:3px solid #6a7b70;padding-top:22px;color:#4d5c51}}.results-body .impact-note{{grid-column:1/-1;color:#216b59}}
.source{{position:absolute;bottom:160px;left:104px;font-size:22px;color:#56645b}}.progress{{position:absolute;bottom:0;left:0;right:0;height:7px;background:#216b59;transform-origin:left center}}
</style><section id="root" data-composition-id="{escape(scene_id, quote=True)}" data-width="{width}" data-height="{height}" data-duration="{duration:.3f}">
<h1 class="headline">{escape(headline)}</h1>{body}<p class="source">{escape(section.headline)} · {escape(source)}</p><div class="progress" aria-hidden="true"></div>
</section><script>
const tl = gsap.timeline({{paused:true}});
tl.fromTo('.headline',{{opacity:0,y:24}},{{opacity:1,y:0,duration:.75,ease:'power2.out'}},.08);
tl.fromTo('.focus',{{opacity:0,y:18}},{{opacity:1,y:0,duration:.85,ease:'power1.out'}},.45);
tl.fromTo('.source',{{opacity:0}},{{opacity:1,duration:.5}},1);
tl.fromTo('.progress',{{scaleX:0}},{{scaleX:1,duration:{duration:.3f},ease:'none'}},0);
window.__timelines[{timeline}] = tl;
</script></template></body></html>"""


def _short(value: str, limit: int) -> str:
    return textwrap.shorten(value.replace("\n", " "), width=limit, placeholder="…")


def _claim(claims, index: int, class_name: str, display: str | None = None) -> str:
    if index >= len(claims):
        return ""
    claim = claims[index]
    return (f'<p class="{class_name}" data-claim-fingerprint="{claim_fingerprint(claim)}">'
            f'{escape(_short(display or claim.text, 300))}</p>')


def _claim_source(claims, index: int, evidence: dict[str, Evidence]) -> str:
    if index >= len(claims):
        return "Evidence in approved briefing"
    pages = [f'p. {evidence[ref].locator["page"]}' for ref in claims[index].evidence_ids
             if ref in evidence and evidence[ref].locator.get("page")]
    return "Source paper " + ", ".join(dict.fromkeys(pages)) if pages else "Evidence in approved briefing"


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
