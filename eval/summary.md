# Persona evaluation

Scenarios: 21 finished, 0 errored.

## Scoring
- O1 rubric coverage: 84/84 = 100.0% of rubric dimensions (the controller visits every question, so this is high by construction)
- O3 verified-quote rate: 84/84 = 100.0%

## Judge accuracy vs the planted key
A miss can be the judge's error or a persona that didn't follow its instruction.

- Overall strict: 152/164 = 92.7%
- Overall lenient: 158/164 = 96.3%

| Persona | Strict | Lenient |
|---|---|---|
| strong_specific | 20/20 = 100.0% | 20/20 = 100.0% |
| rambler | 19/20 = 95.0% | 19/20 = 95.0% |
| vague_generalist | 23/24 = 95.8% | 23/24 = 95.8% |
| bluffer | 23/24 = 95.8% | 23/24 = 95.8% |
| nervous_minimal | 22/24 = 91.7% | 24/24 = 100.0% |
| question_asker | 25/28 = 89.3% | 27/28 = 96.4% |
| hostile | 20/24 = 83.3% | 22/24 = 91.7% |

Confusion table (rows = strict expected, columns = returned):

| Expected | NO_CONCRETE_EXAMPLE | NO_MEASURABLE_OUTCOME | NO_PERSONAL_OWNERSHIP | UNCLEAR_SCOPE | SUFFICIENT | CANNOT_ANSWER | REPEAT_REQUEST | WAIT_REQUEST |
|---|---|---|---|---|---|---|---|---|
| NO_CONCRETE_EXAMPLE | 85 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| NO_MEASURABLE_OUTCOME | 2 | 27 | 2 | 0 | 0 | 0 | 0 | 0 |
| NO_PERSONAL_OWNERSHIP | 1 | 0 | 13 | 0 | 0 | 0 | 0 | 0 |
| UNCLEAR_SCOPE | 0 | 1 | 0 | 8 | 1 | 0 | 0 | 0 |
| SUFFICIENT | 1 | 0 | 0 | 0 | 14 | 0 | 0 | 0 |
| CANNOT_ANSWER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REPEAT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| WAIT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Each element on its own, using all the gaps the judge returned:

- Whole list of gaps exactly right: 122/159 = 76.7%
- Judge quotes that passed the substring check: 163/165 = 98.8%

| Element | Caught when missing | False alarm when present |
|---|---|---|
| concrete_example | 85/89 = 95.5% | 4/70 = 5.7% |
| measurable_outcome | 81/83 = 97.6% | 1/76 = 1.3% |
| personal_ownership | 87/87 = 100.0% | 16/72 = 22.2% |
| clear_scope | 96/103 = 93.2% | 6/56 = 10.7% |

## Persona check
Replies that visibly broke their key (only "I" and numbers can be checked by a script):
- Replies with a break: 15/223 = 6.7%
- personal_ownership missing: 9
- personal_ownership leaked: 5
- measurable_outcome missing: 1

## Follow-ups
- Targeting (asked for an element that really was missing): 132/139 = 95.0%

| Persona | Follow-ups per question | Verdict counts |
|---|---|---|
| strong_specific | 1.08 (n=12) | SUFFICIENT 7, NO_CONCRETE_EXAMPLE 5, UNCLEAR_SCOPE 3, NO_MEASURABLE_OUTCOME 3, NO_PERSONAL_OWNERSHIP 2 |
| rambler | 1.17 (n=12) | SUFFICIENT 6, NO_PERSONAL_OWNERSHIP 4, NO_MEASURABLE_OUTCOME 4, UNCLEAR_SCOPE 4, NO_CONCRETE_EXAMPLE 2 |
| vague_generalist | 1.92 (n=12) | NO_CONCRETE_EXAMPLE 21, NO_MEASURABLE_OUTCOME 3 |
| bluffer | 2.00 (n=12) | NO_CONCRETE_EXAMPLE 19, NO_MEASURABLE_OUTCOME 5 |
| nervous_minimal | 1.83 (n=12) | NO_CONCRETE_EXAMPLE 16, NO_MEASURABLE_OUTCOME 8 |
| question_asker | 1.75 (n=12) | NO_CONCRETE_EXAMPLE 13, NO_MEASURABLE_OUTCOME 6, REPEAT_REQUEST 5, NO_PERSONAL_OWNERSHIP 2, SUFFICIENT 1, UNCLEAR_SCOPE 1 |
| hostile | 1.83 (n=12) | NO_CONCRETE_EXAMPLE 13, NO_PERSONAL_OWNERSHIP 7, NO_MEASURABLE_OUTCOME 3, SUFFICIENT 1 |

## Scores
- strong: mean 3.08 (n=24)
- weak: mean 1.11 (n=36)
- mixed: mean 1.71 (n=24)
- strong_specific: mean 3.17 (n=12)
- rambler: mean 3.00 (n=12)
- vague_generalist: mean 1.17 (n=12)
- bluffer: mean 1.08 (n=12)
- nervous_minimal: mean 1.08 (n=12)
- question_asker: mean 1.58 (n=12)
- hostile: mean 1.83 (n=12)
- Strong group's mean above weak group's mean: yes

## Bluffer trap
Bluffer scores of 4 or 5: 0/12 = 0.0%

## Repeat consistency
- All 4 scores match: not measured yet of turns
- Mean max-min spread: not measured yet

## Fairness
Read against repeat consistency: a changed score may be the model's own noise.
- Score unchanged in both copies: not measured yet of turns
- Mean absolute change: not measured yet

## Judge timing
- judge() p50 1228 ms, p95 2062 ms (n=164), including any retry waits inside call_gemini

## Errored scenarios
None.
