"""
Voice layer on top of Interview, using LiveKit Agents.

LiveKit only moves audio: Silero VAD and the multilingual turn detector decide
when the candidate has finished speaking, Deepgram turns speech into text and
Cartesia turns our text back into speech. There is NO LLM on the session -
every word the agent says is either a prepared question or a template
follow-up returned by Interview.on_answer().

    python prep.py                  # once per candidate: the Gemini prep calls
    python agent.py download-files  # once: downloads the VAD + turn detector models
    python agent.py console         # talk to it through your mic and speakers
    python agent.py dev             # connect to LiveKit Cloud (LIVEKIT_* in .env)

Each call writes three files to reports/, all starting with the call's start time:
    <timestamp>_transcript.json   every line both sides said, verdicts, scores
    <timestamp>_latency.csv       one row of timings per candidate turn
    <timestamp>_report.html       the scorecard (only if the interview finished)
"""

import asyncio
import csv
import json
import math
import os
from datetime import datetime

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, StopResponse, TurnHandlingOptions, cli
from livekit.plugins import cartesia, deepgram, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import llm
import prep
from interview import score_dimension
from interview_session import MAX_FOLLOWUPS
from report import write_html_report
from schemas import Evidence

load_dotenv()

PREPARED_PATH = "prepared_interview.json"
REPORTS_DIR = "reports"

# How long the candidate must be silent before their turn is taken as finished.
# MIN applies when the turn detector thinks they are done, MAX when it thinks
# they are still mid-thought. MIN is raised from LiveKit's 0.5 s because a
# candidate was cut off mid-answer at a short pause; it adds the same amount to
# every reply. MAX is lowered from LiveKit's 3.0 s: a candidate who HAS finished
# but is misread as still thinking waits this long (seen on a test call), so it
# caps the worst-case silence. The cost is that a real mid-answer pause longer
# than this ends the turn early.
MIN_ENDPOINTING_DELAY = 1.0
MAX_ENDPOINTING_DELAY = 2.0
GREETING = ("Hi, I'm an AI interview assistant. This call is being transcribed for the hiring team, "
            "and a person, not the AI, makes the final decision. "
            "I'll ask you a few questions about the projects on your resume.")
CLOSING = ("Thanks, that's all my questions. The transcript of this call now goes to the hiring team, "
           "and a person there will review it and decide the next step.")

# One row per candidate turn. Every value is a measurement, never an estimate;
# an empty cell means that number was not reported for that turn.
LATENCY_COLUMNS = [
    "time", "dimension", "verdict",
    "end_of_utterance_delay_ms",    # LiveKit: end of speech (VAD) -> decision that the turn is over
    "stt_transcription_delay_ms",   # LiveKit: end of speech -> final transcript from Deepgram
    "judge_ms",                     # ours: time inside judge() (one Gemini call)
    "tts_ttfb_ms",                  # LiveKit: text sent to Cartesia -> first audio chunk back
    "user_stopped_speaking_at",     # LiveKit timestamp (epoch seconds)
    "agent_started_speaking_at",    # LiveKit timestamp (epoch seconds) of the reply's first audio frame
    "speech_end_to_first_audio_ms", # the difference of the two timestamps above
]
COMPONENT_LABELS = {
    "end_of_utterance_delay_ms": "End-of-utterance delay (end of speech to turn decision)",
    "stt_transcription_delay_ms": "STT transcription delay (end of speech to final transcript)",
    "judge_ms": "Time inside judge()",
    "tts_ttfb_ms": "TTS time to first byte",
}


def percentile(values: list[float], p: int) -> float:
    """Nearest-rank percentile: the smallest value that at least p% of the values are <= to."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def latency_summary(rows: list[dict]) -> list[str]:
    """One labelled line per number. Nothing here is estimated: a number with
    no measurements is reported as "not measured yet", with what was missing."""
    def measured(column):
        return [r[column] for r in rows if r[column] is not None]

    lines = []
    total = measured("speech_end_to_first_audio_ms")
    if total:
        lines.append(f"End of user speech to first agent audio: p50 {percentile(total, 50):.0f} ms, "
                     f"p95 {percentile(total, 95):.0f} ms (n={len(total)} of {len(rows)} candidate turns). "
                     "Measured from LiveKit's end-of-speech and first-audio-frame timestamps, so it does "
                     "not include playback delay on the listener's side.")
    else:
        missing = [name for name, column in (("the user's end-of-speech timestamp", "user_stopped_speaking_at"),
                                             ("the agent's first-audio timestamp", "agent_started_speaking_at"))
                   if not measured(column)]
        lines.append("End of user speech to first agent audio: not measured yet "
                     f"(missing: {' and '.join(missing) or 'both timestamps on the same turn'}).")
    for column, label in COMPONENT_LABELS.items():
        values = measured(column)
        if values:
            lines.append(f"{label}: p50 {percentile(values, 50):.0f} ms, p95 {percentile(values, 95):.0f} ms "
                         f"(n={len(values)}).")
        else:
            lines.append(f"{label}: not measured yet.")
    return lines


class InterviewAgent(Agent):
    def __init__(self, interview, call: dict, prefix: str):
        super().__init__(instructions="")  # required by Agent, unused: there is no LLM
        self.interview = interview
        self.call = call          # everything saved to <prefix>_transcript.json
        self.prefix = prefix      # reports/<timestamp>
        self.latency_rows: list[dict] = []

    def log(self, speaker: str, text: str, **details) -> dict:
        """Print one timestamped line and add it to the call's message list."""
        now = datetime.now()
        print(f"[{now:%H:%M:%S}] {speaker.upper():>9}: {text}")
        message = {"time": now.isoformat(timespec="seconds"), "speaker": speaker, "text": text, **details}
        self.call["messages"].append(message)
        return message

    async def speak(self, text: str, interruptible: bool = True, **details) -> dict:
        """Log and say one line; return LiveKit's timings for that spoken reply."""
        self.log("agent", text, **details)
        handle = await self.session.say(text, allow_interruptions=interruptible)
        return handle.chat_items[0].metrics if handle.chat_items else {}

    def record_latency(self, message: dict, user: dict, reply: dict) -> None:
        """`user` and `reply` are LiveKit's ChatMessage.metrics for the candidate's
        turn and for our spoken reply to it."""
        def ms(seconds):
            return None if seconds is None else round(seconds * 1000)

        stopped = user.get("stopped_speaking_at")
        started = reply.get("started_speaking_at")
        row = {
            "time": message["time"],
            "dimension": message["dimension"],
            "verdict": message["verdict"],
            "end_of_utterance_delay_ms": ms(user.get("end_of_turn_delay")),
            "stt_transcription_delay_ms": ms(user.get("transcription_delay")),
            "judge_ms": None if message["judge_ms"] is None else round(message["judge_ms"]),
            "tts_ttfb_ms": ms(reply.get("tts_node_ttfb")),
            "user_stopped_speaking_at": stopped,
            "agent_started_speaking_at": started,
            "speech_end_to_first_audio_ms": ms(started - stopped) if stopped and started else None,
        }
        self.latency_rows.append(row)
        path = self.prefix + "_latency.csv"
        is_new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=LATENCY_COLUMNS)
            if is_new:
                writer.writeheader()
            writer.writerow(row)

    def save(self) -> None:
        ended = datetime.now()
        started = datetime.fromisoformat(self.call["started_at"])
        self.call["ended_at"] = ended.isoformat(timespec="seconds")
        self.call["duration_seconds"] = round((ended - started).total_seconds())
        self.call["completed"] = self.interview.done
        self.call["turns"] = [t.model_dump() for t in self.interview.transcript]
        self.call["latency_summary"] = latency_summary(self.latency_rows)
        with open(self.prefix + "_transcript.json", "w", encoding="utf-8") as f:
            json.dump(self.call, f, indent=2, ensure_ascii=False)

    def score_all(self) -> list:
        """Blocking Gemini calls - run via asyncio.to_thread, never on the audio loop."""
        return [score_dimension(dim, turn)
                for dim, turn in zip(self.interview.dimensions, self.interview.transcript)]

    async def finish(self) -> None:
        """After the closing line: score, print the scorecard, write the report."""
        scores = await asyncio.to_thread(self.score_all)
        self.call["scores"] = [s.model_dump() for s in scores]

        print("\n" + "=" * 70)
        print("SCORECARD")
        print("=" * 70)
        for s in scores:
            verified = "verified" if s.quote_verified else "UNSUPPORTED"
            print(f"\n{s.dimension}: {s.score}/5  [{verified}]")
            print(f'  quote: "{s.quote}"')
            print(f"  reasoning: {s.reasoning}")

        timing_notes = latency_summary(self.latency_rows)
        print("\nTIMINGS")
        for note in timing_notes:
            print("  " + note)

        write_html_report(self.prefix + "_report.html", self.call["candidate_name"], self.call["role"],
                          scores, self.interview.transcript, timing_notes, llm.MOCK)
        print(f"\nHTML report written to: {self.prefix}_report.html")
        self.save()

    async def on_enter(self) -> None:
        first = self.interview.start()
        self.log("agent", GREETING, kind="greeting")
        self.log("agent", first, kind="question", dimension=self.interview.questions[0].dimension)
        # Not interruptible: anything picked up while the greeting and first
        # question are still being spoken is background noise, not an answer.
        await self.session.say(f"{GREETING} {first}", allow_interruptions=False)

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = new_message.text_content
        if self.interview.done or not text:
            raise StopResponse()  # interview over, or nothing was heard: say nothing

        question = self.interview.questions[self.interview.index]
        message = self.log("candidate", text, kind="answer", dimension=question.dimension)
        turns_before = len(self.interview.transcript)

        # judge() is a blocking Gemini call, so run it off the event loop.
        next_text = await asyncio.to_thread(self.interview.on_answer, text)

        verdict = self.interview.last_verdict
        question_finished = len(self.interview.transcript) > turns_before
        # "repeat" or "wait" when we stayed on the question to honour that request.
        held = None
        if not question_finished:
            held = {Evidence.REPEAT_REQUEST: "repeat", Evidence.WAIT_REQUEST: "wait"}.get(verdict.missing)
        message["verdict"] = verdict.missing.value if verdict else None
        message["judge_ms"] = self.interview.last_judge_ms
        if verdict is None:
            print(f"  [max {MAX_FOLLOWUPS} follow-ups reached - moving on]")
        elif verdict.sufficient:
            print("  [sufficient]")
        elif question_finished:
            print(f"  [{verdict.missing.value} - moving on]")
        elif held:
            print(f"  [{held} requested]")
        else:
            print(f"  [probing: {verdict.missing.value}]")

        if next_text is None:
            reply_metrics = await self.speak(CLOSING, interruptible=False, kind="closing")
        else:
            kind = "question" if question_finished else held or "followup"
            reply_metrics = await self.speak(
                next_text, kind=kind, dimension=self.interview.questions[self.interview.index].dimension)
        self.record_latency(message, new_message.metrics, reply_metrics)

        if next_text is None:
            try:
                await self.finish()
            finally:
                self.session.shutdown()  # stop taking turns, even if scoring failed
        raise StopResponse()  # we already spoke; never let the session try an LLM reply


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    prepared, interview = prep.load_prepared(PREPARED_PATH)  # no Gemini calls here
    started = datetime.now()
    call = {
        "room": ctx.room.name,
        "candidate_name": prepared["candidate_name"],
        "role": prepared["role"],
        "seniority": prepared["seniority"],
        "started_at": started.isoformat(timespec="seconds"),
        "ended_at": None,
        "duration_seconds": None,
        "completed": False,
        "max_followups": MAX_FOLLOWUPS,
        "pipeline": {"vad": "silero", "turn_detector": "livekit multilingual", "stt": "deepgram nova-3 (en)",
                     "tts": "cartesia (plugin default voice)", "llm": None},
        "messages": [],  # every line, labelled speaker="agent" or "candidate"
        "turns": [],     # one TranscriptTurn per finished question, as scoring expects
        "scores": "not scored yet",  # replaced by the scorecard once the interview finishes
        "latency_summary": [],
    }
    os.makedirs(REPORTS_DIR, exist_ok=True)
    agent = InterviewAgent(interview, call, os.path.join(REPORTS_DIR, f"{started:%Y-%m-%d_%H-%M-%S}"))

    async def save_on_shutdown():
        agent.save()  # also covers a candidate who hangs up mid-interview
        print(f"Call files saved as: {agent.prefix}_*")

    ctx.add_shutdown_callback(save_on_shutdown)

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3", language="en"),
        tts=cartesia.TTS(),
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            endpointing={"min_delay": MIN_ENDPOINTING_DELAY, "max_delay": MAX_ENDPOINTING_DELAY},
        ),
    )
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    if not os.path.exists(PREPARED_PATH):
        raise SystemExit(f"{PREPARED_PATH} not found - run `python prep.py` first to prepare the interview.")
    cli.run_app(server)
