"""
Writes the scorecard out as one self-contained HTML file (inline CSS, no
external assets) so it can be opened straight from the filesystem or emailed
as a single attachment.
"""

import html
from datetime import datetime

from schemas import DimensionScore, TranscriptTurn

_STYLE = """
body { font-family: -apple-system, Segoe UI, Arial, sans-serif; max-width: 760px;
       margin: 40px auto; padding: 0 20px; color: #1a1a1a; background: #fafafa; }
h1 { margin-bottom: 0; }
.subtitle { color: #666; margin-top: 4px; }
.card { background: white; border: 1px solid #ddd; border-radius: 8px;
        padding: 18px 22px; margin: 18px 0; }
.score { font-size: 28px; font-weight: bold; }
.score.unverified { color: #b34700; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
         font-size: 12px; margin-left: 8px; }
.badge.verified { background: #e3f7e3; color: #1a7a1a; }
.badge.unverified { background: #fbe4d5; color: #b34700; }
blockquote { border-left: 3px solid #999; margin: 10px 0; padding: 4px 14px;
             color: #333; font-style: italic; }
.transcript { font-size: 14px; color: #444; white-space: pre-wrap;
              background: #f5f5f5; border-radius: 6px; padding: 10px 14px; }
.q { font-weight: 600; color: #222; }
footer { color: #888; font-size: 13px; margin-top: 30px; }
"""


def write_html_report(
    path: str,
    candidate_name: str,
    jd_title: str,
    scores: list[DimensionScore],
    transcript: list[TranscriptTurn],
    p50_latency_ms: float,
    mock: bool,
) -> None:
    turns_by_dim = {t.dimension: t for t in transcript}
    avg = sum(s.score for s in scores) / len(scores) if scores else 0

    cards = []
    for s in scores:
        turn = turns_by_dim.get(s.dimension)
        badge_class = "verified" if s.quote_verified else "unverified"
        badge_text = "quote verified" if s.quote_verified else "quote UNSUPPORTED"
        score_class = "score" if s.quote_verified else "score unverified"
        transcript_html = ""
        if turn:
            transcript_html = (
                f'<div class="q">Q: {html.escape(turn.question)}</div>'
                f'<div class="transcript">{html.escape(turn.answer)}</div>'
                f'<div style="color:#888;font-size:12px;margin-top:6px;">'
                f"follow-ups asked: {turn.followups_asked}</div>"
            )
        cards.append(f"""
        <div class="card">
          <div><span class="{score_class}">{s.score}/5</span>
               <strong style="margin-left:10px;">{html.escape(s.dimension)}</strong>
               <span class="badge {badge_class}">{badge_text}</span></div>
          <blockquote>&ldquo;{html.escape(s.quote)}&rdquo;</blockquote>
          <div>{html.escape(s.reasoning)}</div>
          {transcript_html}
        </div>""")

    mock_note = " (generated in --mock mode, no API calls made)" if mock else ""

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Screening report - {html.escape(candidate_name)}</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>Candidate Screening Report</h1>
<div class="subtitle">{html.escape(candidate_name)} &middot; {html.escape(jd_title)}
&middot; {datetime.now().strftime("%Y-%m-%d %H:%M")}{mock_note}</div>

<div class="card">
  <div class="score">{avg:.1f}/5</div>
  <div>Average across {len(scores)} rubric dimensions</div>
</div>

{"".join(cards)}

<footer>
  Every score above is tied to a verbatim quote from the transcript, checked
  by exact substring match against what the candidate actually typed - not
  trusted from the model's own claim. p50 turn latency: {p50_latency_ms:.0f} ms.
</footer>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(document)
