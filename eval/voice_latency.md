# Voice latency: judge-v2-frozen

Two completed `agent.py console` calls on 2026-11-01 (starts 16:31 and 16:37), home
Wi-Fi, one speaker, Shaurya's prepared interview. Files: `reports/2026-11-01_16-31-47_*`
and `reports/2026-11-01_16-37-41_*`. p90 and p95 are nearest-rank.

Two earlier attempts that day (15:50, 15:54) are excluded: neither produced a latency
row, because broken IPv6 on a phone hotspot made Gemini calls take about 171 s.

## All measured turns

| Metric (ms) | n | Avg | Median | p90 |
|---|---:|---:|---:|---:|
| End of speech to turn decision (`end_of_utterance_delay_ms`) | 15 | 1199 | 1006 | 2010 |
| Turn decision to first audio (`judge_ms` + `tts_ttfb_ms`) | 14 | 3520 | 1594 | 2891 |
| End of speech to first audio (`speech_end_to_first_audio_ms`) | 15 | 5747 | 3006 | 18285 |
| STT (`stt_transcription_delay_ms`) | 15 | 433 | 441 | 485 |

Total p95: 27184 ms (n=15). Components, p50: judge 1447 ms (n=14), TTS TTFB 127 ms (n=15).

The turn-decision row has n=14 because the follow-up-capped reply makes no judge call.
The components overlap in time, so they do not add up to the total.

## Excluding the two turns affected by one stall

One `judge()` call took 25877 ms (other calls took 1150-2765 ms), and the next turn
measured 18285 ms as a knock-on. See "Turns over 10 s" below.

| Metric (ms) | n | Avg | Median | p90 |
|---|---:|---:|---:|---:|
| End of speech to first audio | 13 | 3133 | 2809 | 4626 |

Total p95 with these turns excluded: 4822 ms (n=13). This exclusion was chosen after
seeing the data, so report it next to the full figures, not in place of them.

## Turns over 10 s

Two of 15 turns, both in call 1 (`2026-11-01_16-31-47`), consecutive. All times are from
that call's latency CSV and transcript JSON. Times are in ms unless marked.

| Candidate spoke | Stopped speaking | Total | End of turn | STT | Judge | TTS | Left over |
|---|---|---:|---:|---:|---:|---:|---:|
| Repeat request 1 | 16:32:50.00 | 27184 | 975 | 435 | **25877** | 127 | 205 |
| Repeat request 2 | 16:33:05.20 | 18285 | 1012 | 438 | 1447 | 129 | **15697** |

"Left over" is total minus end of turn, judge and TTS. On the other 5 turns in call 1 it was
177-405 ms. STT is not subtracted because it overlaps the end-of-turn wait.

**Turn 1: the time was inside `judge()`.** 25877 of 27184 ms (95%). STT, the turn detector
and TTS were all normal for this call.

**Turn 2: the time was queueing behind turn 1, not processing.** The candidate spoke again at
16:33:05 during the silence, while turn 1's `judge()` was still running. Turn 2 could not
start until turn 1's reply finished: the transcript logs it at 16:33:21, about 16 s after
the speech ended. Its own judge call was normal. This corrects an earlier note here, which
guessed it was waiting behind speech still playing; that accounts for only the last few
seconds. So this turn's second repeat request was caused by the stall, not by the test
script, and it made Sarah move on and save the request as the answer (score 1/5).

**Why `judge()` took 25.9 s: not established.** `judge_ms` wraps `call_gemini`, so it would
include retry waits, but nothing saved separates them.

- Console output was not saved, and no file in `reports/` records retries. `llm.py` prints
  retry lines to the console only, so this cannot be confirmed from the files.
- Backoff alone doesn't fit. `llm.py` waits 2-3, 4-5, 8-9, then 16-17 s, so 3 retries wait
  14-17 s and 4 wait at least 30 s. 25.9 s would need 3 retries plus 9-12 s spent in requests.
- A per-minute 429 is unlikely: the session had made only 2 Gemini calls in the prior 40 s,
  against a limit of 15 per minute. Other use of the project at that moment is not ruled out.
- A 503 retry or one slow Gemini response remain possible.
- The IPv6 fault that caused the 171 s hangs earlier is not a match: that lost about 170 s,
  and a connection check on this Wi-Fi showed no IPv6 addresses for Gemini.

No API calls were made for this analysis.

## Comparison

| Source | p50 total (ms) | p95 total (ms) | n |
|---|---:|---:|---:|
| Earlier judge, `reports/2026-10-05_04-18-15_*` | 2772 | 4315 | 6 of 12 turns |
| 2026-11-01, all turns | 3006 | 27184 | 15 |
| 2026-11-01, excluding stall turns | 2809 | 4822 | 13 |

The earlier call is the one previously called "4 Oct": its files are dated 5 Oct 04:18
local time. Only 6 of its 12 turns have a measured total.

Freeze-Omni figures as supplied for comparison, not checked against the paper:
non-statistical latency about 160-320 ms; statistical latency avg 745, median 753, p90 1020 ms.

Comparison limits:

- End-of-utterance is set by `MIN_ENDPOINTING_DELAY = 1.0` s and `MAX_ENDPOINTING_DELAY = 2.0` s,
  a design choice to avoid cutting candidates off. It is not comparable to a model's own speed.
- Freeze-Omni's statistical latency is a speech-to-speech model's inference. Ours is a text
  classification call to Gemini plus TTS first byte. The two are shown side by side, not
  as a like-for-like measure.
- Small sample, one speaker, one network. 4 Oct and today are not a controlled comparison.
