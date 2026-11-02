# Dataset splits

This guide maps the project's data to splits. No files are moved; every path is
relative to the repo root.

| Split | Inputs | Interviews | Use |
|---|---|---|---|
| Train | None | 0 | SARAH is prompt-based, so no model is trained |
| Validation | `data/resume_alex.txt` | 7 | Tuning the judge before it was frozen |
| Test (held-out) | `data/resume_priya.pdf`, `data/resume_shaurya.pdf` | 14 | Final results |

## Train

None. SARAH uses a hosted LLM through fixed prompts, and no weights are fitted.

## Validation

- Resume: `data/resume_alex.txt`
- Transcripts: `eval/transcripts/resume_alex_*` (7 interviews, one per persona)

These interviews were used to tune the judge before it was frozen at git tag
`judge-v2-frozen`. Six of the seven saved transcripts used an earlier judge; only
`resume_alex_hostile_1` used the frozen version. Earlier tuning runs are in `eval/old/`.

## Test (held-out)

- Resumes: `data/resume_priya.pdf`, `data/resume_shaurya.pdf`
- Transcripts: `eval/transcripts/resume_priya_*`, `eval/transcripts/resume_shaurya_*`
- Size: 14 interviews, 56 scored turns, 110 judged replies

All 14 interviews ran on the frozen judge with no further tuning.

## Other data

- `data/job_description.txt`: the job description used for every interview
- `eval/prepared/`: the rubric and questions prepared for each resume
- `eval/human_labels.csv`, `eval/human_labels.xlsx`, `eval/human_labels_friend.xlsx`:
  28 human-rated test turns, scored by two people without Sarah's scores or persona
  names on the sheet. One rater is the system's author, who had seen some results
  beforehand, and half the turns come from that author's resume
- `reports/*latency.csv`: per-turn latency logs from the voice calls

The candidates in the transcripts are simulated LLM personas with planted answer keys.
See the Evaluation section of the main `README.md` for the method and limits.
