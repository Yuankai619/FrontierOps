"""Publish only reader-facing artifacts outside the internal Run store."""

import json
from pathlib import Path
import shutil
import tempfile
from typing import Mapping


class FilesystemOutputPublisher:
    def publish(self, run_dir: Path, output_root: Path, outputs: Mapping[str, str]) -> Path:
        root = output_root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".frontier-publish-", dir=root))
        try:
            published: dict[str, str] = {}
            render_dir = run_dir / "05-render"
            if "html" in outputs:
                target = temporary / "html"
                target.mkdir()
                shutil.copy2(render_dir / "briefing.html", target / "index.html")
                for relative in ("assets", "visuals"):
                    source = render_dir / relative
                    if source.is_dir():
                        shutil.copytree(source, target / relative)
                published["html"] = "html/index.html"
            if "slides" in outputs:
                shutil.copytree(render_dir / "open-slide", temporary / "slides")
                published["slides"] = "slides/slides/frontier-briefing/index.tsx"
            if "video_preview" in outputs:
                shutil.copytree(render_dir / "hyperframes", temporary / "video")
                published["video_preview"] = "video/index.html"
            manifest = {"schema_version": "0.1", "source_run": str(run_dir.resolve()),
                        "outputs": published, "video_finalized": False}
            (temporary / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            (temporary / "index.html").write_text(_landing(published), encoding="utf-8")
            target = root / run_dir.name
            number = 2
            while target.exists():
                target = root / f"{run_dir.name}-{number}"
                number += 1
            temporary.rename(target)
            return target
        except Exception:
            shutil.rmtree(temporary)
            raise


def _landing(outputs: Mapping[str, str]) -> str:
    links = []
    if "html" in outputs:
        links.append('<li><a href="html/index.html">閱讀互動論文解釋</a></li>')
    if "slides" in outputs:
        links.append('<li>OpenSlide 專案：進入 <code>slides/</code> 執行 '
                     '<code>npm install</code>、<code>npm run build</code>、'
                     '<code>npm run preview</code>。</li>')
    if "video_preview" in outputs:
        links.append('<li>HyperFrames 影片預覽：進入 <code>video/</code> 執行 '
                     '<code>npx hyperframes check</code> 與 '
                     '<code>npx hyperframes preview</code>；尚未產出最終 MP4。</li>')
    content = "\n".join(links) or "<li>目前沒有可發布的媒體。</li>"
    return ('<!doctype html><html lang="zh-Hant"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>FrontierOps 研究簡報</title>'
            '<style>body{max-width:760px;margin:7vh auto;padding:0 25px;'
            'background:#f8f7f2;color:#182723;font:18px/1.7 system-ui}'
            'h1{font:700 44px Georgia,serif}li{padding:14px 0;border-top:1px solid #ccd4cc}'
            'a{color:#1d5b50}code{font-size:.82em}</style>'
            '<h1>研究簡報成果</h1><p>此目錄只放閱讀與展示所需成果；'
            '內部證據、篩選紀錄與版本留在 Run 中。</p><ul>'
            + content + '</ul><p><a href="manifest.json">查看成果清單</a></p></html>')
