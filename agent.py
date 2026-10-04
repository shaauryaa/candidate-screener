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

Each call is saved to transcripts/ as JSON.
"""

import asyncio
import json
import os
from datetime import datetime

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, StopResponse, TurnHandlingOptions, cli
from livekit.plugins import cartesia, deepgram, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import prep
from interview_session import MAX_FOLLOWUPS
from schemas import Evidence

load_dotenv()

PREPARED_PATH = "prepared_interview.json"
TRANSCRIPTS_DIR = "transcripts"
GREETING = "Hi, thanks for joining. I'll ask you a few questions about the projects on your resume."
CLOSING = "Thanks, that's all my questions. The hiring team will review this and get back to you."


class InterviewAgent(Agent):
    def __init__(self, interview, call: dict, call_path: str):
        super().__init__(instructions="")  # required by Agent, unused: there is no LLM
        self.interview = interview
        self.call = call            # everything saved to transcripts/ for this call
        self.call_path = call_path

    def log(self, speaker: str, text: str, **details) -> dict:
        """Print one timestamped line and add it to the call's message list."""
        now = datetime.now()
        print(f"[{now:%H:%M:%S}] {speaker.upper():>9}: {text}")
        message = {"time": now.isoformat(timespec="seconds"), "speaker": speaker, "text": text, **details}
        self.call["messages"].append(message)
        return message

    def save(self) -> None:
        ended = datetime.now()
        started = datetime.fromisoformat(self.call["started_at"])
        self.call["ended_at"] = ended.isoformat(timespec="seconds")
        self.call["duration_seconds"] = round((ended - started).total_seconds())
        self.call["completed"] = self.interview.done
        self.call["turns"] = [t.model_dump() for t in self.interview.transcript]
        os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
        with open(self.call_path, "w", encoding="utf-8") as f:
            json.dump(self.call, f, indent=2, ensure_ascii=False)

    async def on_enter(self) -> None:
        first = self.interview.start()
        self.log("agent", GREETING, kind="greeting")
        self.log("agent", first, kind="question", dimension=self.interview.questions[0].dimension)
        await self.session.say(f"{GREETING} {first}")

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
        repeating = not question_finished and verdict.missing == Evidence.REPEAT_REQUEST
        message["verdict"] = verdict.missing.value if verdict else None
        message["judge_ms"] = self.interview.last_judge_ms
        if verdict is None:
            print(f"  [max {MAX_FOLLOWUPS} follow-ups reached - moving on]")
        elif verdict.sufficient:
            print("  [sufficient]")
        elif question_finished:
            print(f"  [{verdict.missing.value} - moving on]")
        elif repeating:
            print("  [repeat requested]")
        else:
            print(f"  [probing: {verdict.missing.value}]")

        if next_text is None:
            self.log("agent", CLOSING, kind="closing")
            await self.session.say(CLOSING)
            self.save()
            self.session.shutdown()  # drains the closing line, then stops taking turns
        else:
            kind = "question" if question_finished else "repeat" if repeating else "followup"
            self.log("agent", next_text, kind=kind, dimension=self.interview.questions[self.interview.index].dimension)
            await self.session.say(next_text)
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
    }
    name = "".join(c if c.isalnum() else "_" for c in prepared["candidate_name"])
    agent = InterviewAgent(interview, call, os.path.join(TRANSCRIPTS_DIR, f"{started:%Y-%m-%d_%H-%M-%S}_{name}.json"))

    async def save_on_shutdown():
        agent.save()  # also covers a candidate who hangs up mid-interview
        print(f"Call transcript saved to: {agent.call_path}")

    ctx.add_shutdown_callback(save_on_shutdown)

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3", language="en"),
        tts=cartesia.TTS(),
        turn_handling=TurnHandlingOptions(turn_detection=MultilingualModel()),
    )
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    if not os.path.exists(PREPARED_PATH):
        raise SystemExit(f"{PREPARED_PATH} not found - run `python prep.py` first to prepare the interview.")
    cli.run_app(server)
