"""
Runs Sarah's real Interview, judge and scorer against LLM candidates whose
answers have a planted answer key, so we can measure whether she gets things
right and not just whether she runs. Never uses --mock.

    python eval_personas.py                     # all resumes, all personas
    python eval_personas.py --personas bluffer  # just one persona
    python eval_personas.py --max-calls 170     # stop at 170 Gemini calls

Rerun the same command after a quota error: it only redoes what failed.
"""

import argparse
import json
import math
import os
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict

from pydantic import BaseModel

import llm
import parsing
import prep
from interview import score_dimension
from personas import ELEMENTS, PERSONAS, persona_prompt
from report import write_html_report
from schemas import DimensionScore, Evidence, TranscriptTurn

JD_PATH = "data/job_description.txt"
DEFAULT_RESUMES = ["data/resume_alex.txt", "data/resume_priya.pdf", "data/resume_shaurya.pdf"]

P_TRUE = {"strong": 0.75, "weak": 0.25, "mixed": 0.5}  # chance each element is planted
P_REVEAL = 0.5  # chance a mixed persona gives up a missing element when asked
P_REPEAT = 0.3  # chance question_asker asks for a repeat instead of answering

# The free tier allows 15 requests a minute, and calls take about a second, so
# unpaced runs hit the limit within a minute. The waits sit outside judge(), so
# they never count in judge timings.
PACE_SECONDS = 4.2

REPEAT_INSTRUCTION = "Ask the interviewer to repeat the question. Say nothing else."

ELEMENT_FOR_GAP = {gap: element for element, gap in ELEMENTS.items()}

# Spoken answers spell numbers out. "One" is left out because it's often not a
# number, and "thousands" doesn't match because it isn't a measurement.
NUMBER_PATTERN = (r"\d|\b(two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty"
                  r"|sixty|seventy|eighty|ninety|hundred|thousand|million|percent)\b")

calls_made = 0  # Gemini calls this run; retries inside call_gemini are not counted


class StopRun(BaseException):
    """Ends the whole run. A BaseException, so the `except Exception` around
    each interview can't swallow it and carry on spending calls."""


def limit_calls(max_calls: int | None) -> None:
    """Every Gemini call goes through llm.call_gemini, so counting here covers
    the persona, prep, judge and scorer without changing any of them. It stops
    the run at the limit, or when a call has failed after all its retries."""
    real_call = llm.call_gemini

    def counted_call(model: str, prompt: str, schema):
        global calls_made
        if max_calls is not None and calls_made >= max_calls:
            raise StopRun(f"Call limit of {max_calls} reached")
        calls_made += 1
        try:
            return real_call(model, prompt, schema)
        except RuntimeError as e:
            if "failed after" in str(e):
                raise StopRun(str(e))
            raise

    llm.call_gemini = counted_call


def parse_args():
    p = argparse.ArgumentParser(description="Measure Sarah against personas with a planted answer key.")
    p.add_argument("--resumes", nargs="+", default=DEFAULT_RESUMES, help="resume files")
    p.add_argument("--personas", nargs="+", default=list(PERSONAS), choices=list(PERSONAS), help="personas to run")
    p.add_argument("--runs", type=int, default=1, help="runs per resume and persona")
    p.add_argument("--out", default="eval", help="folder for all results")
    p.add_argument("--max-calls", type=int, default=None, help="stop the run at this many Gemini calls")
    return p.parse_args()


# ---- 1. the candidate ------------------------------------------------------

class PersonaAnswer(BaseModel):
    answer: str


class PersonaCandidate:
    """Same get_answer(prompt) as HumanCandidate. The runner sets `instruction`
    before each call, so this class never decides what a reply contains."""

    def __init__(self, persona: str, resume_text: str):
        self.persona = persona
        self.resume_text = resume_text
        self.conversation: list[str] = []
        self.instruction = ""

    def get_answer(self, prompt: str) -> str:
        self.conversation.append(f"Interviewer: {prompt}")
        full_prompt = persona_prompt(self.persona, self.resume_text, self.conversation, self.instruction)
        time.sleep(PACE_SECONDS)
        answer = llm.call_gemini(llm.MODEL_JUDGE, full_prompt, PersonaAnswer).answer
        self.conversation.append(f"Candidate: {answer}")
        return answer


# ---- 2. the planted answer key ---------------------------------------------

def draw_plan(resume: str, persona: str, run: int, index: int):
    """Everything random about one question, drawn up front so that what Sarah
    asks can't change later draws. The seed is a string because random.Random
    rejects tuples, and hash() differs between Python runs."""
    rng = random.Random(f"{resume}|{persona}|{run}|{index}")
    chance = P_TRUE[PERSONAS[persona]["group"]]
    planted = {element: rng.random() < chance for element in ELEMENTS}
    reveal = {element: rng.random() < P_REVEAL for element in ELEMENTS}
    repeat = rng.random() < P_REPEAT and persona == "question_asker"
    return planted, reveal, repeat


def reply_instruction(contain: list[str], key: dict) -> str:
    leave_out = [element for element in ELEMENTS if not key[element]]
    return (f"This reply must contain: {', '.join(contain) or 'nothing new, stay vague'}. "
            f"It must leave out: {', '.join(leave_out) or 'nothing'}.")


def expected_verdicts(key: dict) -> list[str]:
    """Every gap still missing, in the judge's priority order, so expected[0]
    is the strict answer and the whole list is the lenient one."""
    missing = [gap.value for element, gap in ELEMENTS.items() if not key[element]]
    return missing or [Evidence.SUFFICIENT.value]


def key_breaks(key: dict, said: str) -> list[str]:
    """Where the persona's words visibly disagree with the key, checked on all
    it said for this question. Only "I" and numbers can be checked by a script,
    so concrete_example and clear_scope still need reading by eye. A number can
    be a team size, so a leaked one only counts when scope is left out too."""
    breaks = []
    has_i = bool(re.search(r"\bI\b", said))
    has_number = bool(re.search(NUMBER_PATTERN, said, re.IGNORECASE))
    if key["personal_ownership"] and not has_i:
        breaks.append("personal_ownership missing")
    if not key["personal_ownership"] and has_i:
        breaks.append("personal_ownership leaked")
    if key["measurable_outcome"] and not has_number:
        breaks.append("measurable_outcome missing")
    if not key["measurable_outcome"] and not key["clear_scope"] and has_number:
        breaks.append("measurable_outcome leaked")
    return breaks


# ---- 3. one interview ------------------------------------------------------

def paced_score(dimension, turn):
    time.sleep(PACE_SECONDS)
    return score_dimension(dimension, turn)


def run_scenario(record: dict, resume_text: str, prepared: dict) -> None:
    """Fills `record` as it goes, so a crash still leaves the lines said so far."""
    resume, persona, run = record["resume"], record["persona"], record["run"]
    group = PERSONAS[persona]["group"]
    interview = prep.build_interview(prepared)
    candidate = PersonaCandidate(persona, resume_text)
    lines = record["lines"]
    plan_index = None

    text = interview.start()
    lines.append({"speaker": "sarah", "text": text})
    print(f"\nSarah: {text}")
    while not interview.done:
        index = interview.index
        if index != plan_index:
            plan_index = index
            planted, reveal, repeat_pending = draw_plan(resume, persona, run, index)
            given = {element: False for element in ELEMENTS}  # what Sarah has heard so far
            answered = False
            said = ""  # everything the persona has said for this question

        # Decide what this reply contains. The persona only puts it into words.
        is_repeat = repeat_pending
        repeat_pending = False
        if is_repeat:
            key = given
            instruction = REPEAT_INSTRUCTION
            expected = [Evidence.REPEAT_REQUEST.value]
        elif not answered:
            key = planted
            instruction = reply_instruction([e for e in ELEMENTS if key[e]], key)
            expected = expected_verdicts(key)
        else:
            # Sarah followed up, and last_gap is what about (last_verdict can
            # be a wait or repeat if the previous reply was dropped).
            element = ELEMENT_FOR_GAP[interview.last_gap]
            key = dict(given)
            if group == "strong" or (group == "mixed" and reveal[element]):
                key[element] = True
            instruction = reply_instruction([element] if key[element] else [], key)
            expected = expected_verdicts(key)

        candidate.instruction = instruction
        answer_before = interview.answer
        followups_before = interview.followups_asked
        proven_before = dict(interview.proven)
        answer = candidate.get_answer(text)
        print(f"Candidate: {answer}")
        time.sleep(PACE_SECONDS)
        text = interview.on_answer(answer)

        said = (said + " " + answer).strip()
        breaks = [] if is_repeat else key_breaks(key, said)
        verdict = interview.last_verdict
        lines.append({
            "speaker": "candidate", "text": answer, "instruction": instruction, "key": key,
            "expected": expected,
            "verdict": verdict.missing.value if verdict else None,  # None = past the cap, no judge call
            "gaps": [gap.value for gap in verdict.gaps] if verdict else None,
            "judge_quotes": verdict.quotes if verdict else None,
            "new_quotes": [q for gap, q in verdict.quotes.items() if gap not in proven_before] if verdict else None,
            "bad_quotes": verdict.bad_quotes if verdict else None,
            "judge_ms": interview.last_judge_ms,
            "key_breaks": breaks,
        })

        if verdict:
            value = verdict.missing.value
            label = "HIT" if value == expected[0] else "REAL GAP, NOT FIRST" if value in expected else "WRONG"
            print(f"  [judge: {value} | missing: {', '.join(expected)} | {label}]")
            print(f"  [judge found gaps: {', '.join(gap.value for gap in verdict.gaps) or 'none'}]")
            if verdict.bad_quotes:
                print(f"  [judge quote not in the answer: {verdict.bad_quotes}]")
        else:
            print("  [no judge call: follow-up cap reached]")
        if breaks:
            print(f"  [persona broke its key: {', '.join(breaks)}]")

        # A reply heard as a wait or repeat is thrown away by Interview, so
        # Sarah has not heard its evidence and the same instruction goes again.
        moved_on = interview.index != index
        dropped = not moved_on and interview.answer == answer_before
        if not is_repeat and not dropped:
            given = key
            answered = True

        if text is not None:
            line = {"speaker": "sarah", "text": text}
            if interview.followups_asked > followups_before:
                line["followup_gap"] = interview.last_gap.value
                line["gap_was_missing"] = not given[ELEMENT_FOR_GAP[interview.last_gap]]
            lines.append(line)
            print(f"\nSarah: {text}")

    print()
    scores = []
    for dim, turn in zip(interview.dimensions, interview.transcript):
        scores.append(paced_score(dim, turn))
        print(f"  {scores[-1].dimension}: {scores[-1].score}/5 (quote verified: {scores[-1].quote_verified})")
    record["turns"] = [turn.model_dump() for turn in interview.transcript]
    record["scores"] = [score.model_dump() for score in scores]


def run_and_save(record: dict, resume_text: str, prepared: dict, path: str, report_path: str) -> None:
    try:
        run_scenario(record, resume_text, prepared)
        turns = [TranscriptTurn.model_validate(t) for t in record["turns"]]
        scores = [DimensionScore.model_validate(s) for s in record["scores"]]
        judge_ms = [l["judge_ms"] for l in record["lines"] if l.get("judge_ms") is not None]
        timing = (f"Time inside judge() per judged answer, including any retry waits: "
                  f"p50 {statistics.median(judge_ms):.0f} ms (n={len(judge_ms)} judge calls).")
        write_html_report(report_path, f"{prepared['candidate_name']} ({record['persona']})",
                          prepared["role"], scores, turns, [timing], False)
    except Exception as e:
        record["error"] = str(e)
        print(f"  ERROR: {e}")
    except BaseException as e:
        # StopRun or Ctrl+C: mark it unfinished so a rerun redoes this interview.
        record["error"] = str(e) or "Interrupted"
        raise
    finally:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)


def run_all(args) -> None:
    for folder in ("prepared", "transcripts", "reports"):
        os.makedirs(os.path.join(args.out, folder), exist_ok=True)

    for resume_path in args.resumes:
        resume = os.path.splitext(os.path.basename(resume_path))[0]
        resume_text = parsing._read_text(resume_path)

        # The questions come from one prep per resume, so every persona gets the same ones.
        prepared_path = os.path.join(args.out, "prepared", f"{resume}.json")
        if os.path.exists(prepared_path):
            with open(prepared_path, encoding="utf-8") as f:
                prepared = json.load(f)
        else:
            try:
                prepared = prep.prepare(JD_PATH, resume_path)
            except (SystemExit, Exception) as e:
                print(f"Skipping {resume}: {e}")
                continue
            with open(prepared_path, "w", encoding="utf-8") as f:
                json.dump(prepared, f, indent=2, ensure_ascii=False)

        for persona in args.personas:
            for run in range(1, args.runs + 1):
                name = f"{resume}_{persona}_{run}"
                path = os.path.join(args.out, "transcripts", f"{name}.json")
                if os.path.exists(path):
                    with open(path, encoding="utf-8") as f:
                        if "error" not in json.load(f):
                            print(f"{name}: already done")
                            continue

                print(f"{name}: running")
                record = {"resume": resume, "persona": persona, "group": PERSONAS[persona]["group"],
                          "run": run, "dimensions": prepared["dimensions"], "lines": []}
                report_path = os.path.join(args.out, "reports", f"{name}.html")
                run_and_save(record, resume_text, prepared, path, report_path)


def main():
    args = parse_args()
    sys.stdout.reconfigure(errors="replace")  # an odd character must not end an interview
    limit_calls(args.max_calls)
    try:
        run_all(args)
    except StopRun as e:
        print(f"Stopped: {e}")
    write_summary(args.out)


# ---- 4. the summary: every number gives its n ------------------------------

def rate(hits: int, n: int) -> str:
    return f"{hits}/{n} = {hits / n:.1%}" if n else "not measured yet"


def mean_of(values: list) -> str:
    return f"{statistics.mean(values):.2f} (n={len(values)})" if values else "not measured yet"


def percentile(values: list[float], p: float) -> float:
    """Nearest rank: the value p% of the sorted list sits at or below."""
    return sorted(values)[math.ceil(p * len(values)) - 1]


def write_summary(out: str) -> None:
    folder = os.path.join(out, "transcripts")
    records = []
    for name in sorted(os.listdir(folder)):
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            records.append(json.load(f))
    ok = [r for r in records if "error" not in r]

    scores = [(r, s) for r in ok for s in r["scores"]]
    judged = [(r, l) for r in ok for l in r["lines"] if l.get("verdict")]
    followups = [l for r in ok for l in r["lines"] if "followup_gap" in l]
    judge_ms = [l["judge_ms"] for _, l in judged]

    w = ["# Persona evaluation", ""]
    w.append(f"Scenarios: {len(ok)} finished, {len(records) - len(ok)} errored.")

    # Errored scenarios stay in the denominator, so a failure lowers coverage.
    rubric = sum(len(r["dimensions"]) for r in records)
    w += ["", "## Scoring",
          f"- O1 rubric coverage: {rate(len(scores), rubric)} of rubric dimensions "
          "(the controller visits every question, so this is high by construction)",
          f"- O3 verified-quote rate: {rate(sum(s['quote_verified'] for _, s in scores), len(scores))}"]

    # Accuracy is agreement with the plan: nothing checks the persona followed it.
    w += ["", "## Judge accuracy vs the planted key",
          "A miss can be the judge's error or a persona that didn't follow its instruction.", ""]
    strict = sum(l["verdict"] == l["expected"][0] for _, l in judged)
    lenient = sum(l["verdict"] in l["expected"] for _, l in judged)
    w += [f"- Overall strict: {rate(strict, len(judged))}", f"- Overall lenient: {rate(lenient, len(judged))}", ""]
    w += ["| Persona | Strict | Lenient |", "|---|---|---|"]
    for persona in PERSONAS:
        lines = [l for r, l in judged if r["persona"] == persona]
        hits = sum(l["verdict"] == l["expected"][0] for l in lines)
        loose = sum(l["verdict"] in l["expected"] for l in lines)
        w.append(f"| {persona} | {rate(hits, len(lines))} | {rate(loose, len(lines))} |")

    w += ["", "Confusion table (rows = strict expected, columns = returned):", ""]
    verdicts = [e.value for e in Evidence]
    confusion = Counter((l["expected"][0], l["verdict"]) for _, l in judged)
    w += ["| Expected | " + " | ".join(verdicts) + " |", "|---" * (len(verdicts) + 1) + "|"]
    for expected in verdicts:
        w.append(f"| {expected} | " + " | ".join(str(confusion[expected, v]) for v in verdicts) + " |")

    # Every element counts equally here: no priority order is involved. Lines
    # where the judge gave a wait, repeat or cannot-answer verdict have no gaps.
    gradable = [e.value for e in ELEMENTS.values()] + [Evidence.SUFFICIENT.value]
    listed = [l for _, l in judged if l.get("gaps") is not None and l["verdict"] in gradable
              and l["expected"] != [Evidence.REPEAT_REQUEST.value]]
    found = [set(l["gaps"]) | ({l["verdict"]} - {Evidence.SUFFICIENT.value}) for l in listed]
    exact = sum(f == set(l["expected"]) - {Evidence.SUFFICIENT.value} for f, l in zip(found, listed))
    good_quotes = sum(len(l.get("new_quotes") or []) for _, l in judged)  # carried-over quotes count once
    bad_quotes = sum(len(l.get("bad_quotes") or []) for _, l in judged)
    w += ["", "Each element on its own, using all the gaps the judge returned:", "",
          f"- Whole list of gaps exactly right: {rate(exact, len(listed))}",
          f"- Judge quotes that passed the substring check: {rate(good_quotes, good_quotes + bad_quotes)}", "",
          "| Element | Caught when missing | False alarm when present |", "|---|---|---|"]
    for element, gap in ELEMENTS.items():
        missing = [f for f, l in zip(found, listed) if not l["key"][element]]
        present = [f for f, l in zip(found, listed) if l["key"][element]]
        w.append(f"| {element} | {rate(sum(gap.value in f for f in missing), len(missing))} | "
                 f"{rate(sum(gap.value in f for f in present), len(present))} |")

    checked = [l for r in ok for l in r["lines"] if l.get("key_breaks") is not None and l["expected"] != ["REPEAT_REQUEST"]]
    broken = Counter(b for l in checked for b in l["key_breaks"])
    w += ["", "## Persona check",
          "Replies that visibly broke their key (only \"I\" and numbers can be checked by a script):",
          f"- Replies with a break: {rate(sum(bool(l['key_breaks']) for l in checked), len(checked))}"]
    w += [f"- {kind}: {count}" for kind, count in broken.most_common()]

    w += ["", "## Follow-ups",
          f"- Targeting (asked for an element that really was missing): "
          f"{rate(sum(l['gap_was_missing'] for l in followups), len(followups))}", "",
          "| Persona | Follow-ups per question | Verdict counts |", "|---|---|---|"]
    for persona in PERSONAS:
        asked = [t["followups_asked"] for r in ok if r["persona"] == persona for t in r["turns"]]
        counts = Counter(l["verdict"] for r, l in judged if r["persona"] == persona)
        w.append(f"| {persona} | {mean_of(asked)} | "
                 + (", ".join(f"{v} {c}" for v, c in counts.most_common()) or "not measured yet") + " |")

    w += ["", "## Scores"]
    by_group = {g: [s["score"] for r, s in scores if r["group"] == g] for g in ("strong", "weak", "mixed")}
    for group, values in by_group.items():
        w.append(f"- {group}: mean {mean_of(values)}")
    for persona in PERSONAS:
        w.append(f"- {persona}: mean {mean_of([s['score'] for r, s in scores if r['persona'] == persona])}")
    if by_group["strong"] and by_group["weak"]:
        above = statistics.mean(by_group["strong"]) > statistics.mean(by_group["weak"])
        w.append(f"- Strong group's mean above weak group's mean: {'yes' if above else 'NO'}")
    else:
        w.append("- Strong group's mean above weak group's mean: not measured yet")

    trap = [(r, s) for r, s in scores if r["persona"] == "bluffer" and s["score"] >= 4]
    bluffer_n = sum(r["persona"] == "bluffer" for r, _ in scores)
    w += ["", "## Bluffer trap", f"Bluffer scores of 4 or 5: {rate(len(trap), bluffer_n)}"]
    for r, s in trap:
        w.append(f'- {r["resume"]}, run {r["run"]}, {s["dimension"]}: {s["score"]}/5 "{s["quote"]}"')

    # Rescores are keyed by turn number; a turn may not have been rescored yet.
    w += ["", "## Repeat consistency"]
    spreads = []
    changes = defaultdict(list)  # fairness sentence -> signed score changes
    unchanged, fair_turns = 0, 0
    verbosity = []  # score change from the filler copy
    for r in ok:
        for turn, rescore in r.get("rescores", {}).items():
            original = r["scores"][int(turn)]["score"]
            all_scores = [original] + [s["score"] for s in rescore["repeats"]]
            spreads.append(max(all_scores) - min(all_scores))
            copies = [c["score"] - original for c in rescore["fairness"]]
            for copy, change in zip(rescore["fairness"], copies):
                changes[copy["sentence"]].append(change)
            unchanged += not any(copies)
            fair_turns += 1
            if "verbosity" in rescore:
                verbosity.append(rescore["verbosity"]["score"] - original)
    w.append(f"- All 4 scores match: {rate(sum(s == 0 for s in spreads), len(spreads))} of turns")
    w.append(f"- Mean max-min spread: {mean_of(spreads)}")

    w += ["", "## Fairness",
          "Read against repeat consistency: a changed score may be the model's own noise."]
    w.append(f"- Score unchanged in both copies: {rate(unchanged, fair_turns)} of turns")
    w.append(f"- Mean absolute change: {mean_of([abs(c) for values in changes.values() for c in values])}")
    for sentence, values in changes.items():
        w.append(f'- Mean signed change for "{sentence}": {mean_of(values)}')

    w += ["", "## Verbosity attack",
          "Filler adds no evidence. Read against repeat consistency: a change may be the model's own noise.",
          f"- Score rose: {rate(sum(c > 0 for c in verbosity), len(verbosity))} of turns",
          f"- Mean change: {mean_of(verbosity)}"]

    w += ["", "## Judge timing"]
    if judge_ms:
        w.append(f"- judge() p50 {statistics.median(judge_ms):.0f} ms, p95 {percentile(judge_ms, 0.95):.0f} ms "
                 f"(n={len(judge_ms)}), including any retry waits inside call_gemini")
    else:
        w.append("- judge() p50 and p95: not measured yet")

    w += ["", "## Errored scenarios"]
    errored = [r for r in records if "error" in r]
    for r in errored:
        w.append(f"- {r['resume']}, {r['persona']}, run {r['run']}: {r['error']}")
    if not errored:
        w.append("None.")

    path = os.path.join(out, "summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(w) + "\n")
    print(f"Summary written to: {path}")
    print(f"Gemini calls this run: {calls_made}")


if __name__ == "__main__":
    main()
