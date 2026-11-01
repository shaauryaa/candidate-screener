# Persona evaluation

Scenarios: 14 finished, 0 errored.

## Scoring
- O1 rubric coverage: 56/56 = 100.0% of rubric dimensions (the controller visits every question, so this is high by construction)
- O3 verified-quote rate: 56/56 = 100.0%

## Judge accuracy vs the planted key
A miss can be the judge's error or a persona that didn't follow its instruction.

- Overall strict: 99/107 = 92.5%
- Overall lenient: 103/107 = 96.3%

| Persona | Strict | Lenient |
|---|---|---|
| strong_specific | 13/13 = 100.0% | 13/13 = 100.0% |
| rambler | 13/13 = 100.0% | 13/13 = 100.0% |
| vague_generalist | 15/16 = 93.8% | 15/16 = 93.8% |
| bluffer | 16/16 = 100.0% | 16/16 = 100.0% |
| nervous_minimal | 14/16 = 87.5% | 16/16 = 100.0% |
| question_asker | 16/17 = 94.1% | 16/17 = 94.1% |
| hostile | 12/16 = 75.0% | 14/16 = 87.5% |

Confusion table (rows = strict expected, columns = returned):

| Expected | NO_CONCRETE_EXAMPLE | NO_MEASURABLE_OUTCOME | NO_PERSONAL_OWNERSHIP | UNCLEAR_SCOPE | SUFFICIENT | CANNOT_ANSWER | REPEAT_REQUEST | WAIT_REQUEST |
|---|---|---|---|---|---|---|---|---|
| NO_CONCRETE_EXAMPLE | 63 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| NO_MEASURABLE_OUTCOME | 1 | 13 | 2 | 0 | 0 | 0 | 0 | 0 |
| NO_PERSONAL_OWNERSHIP | 1 | 0 | 8 | 0 | 0 | 0 | 0 | 0 |
| UNCLEAR_SCOPE | 0 | 0 | 0 | 5 | 1 | 0 | 0 | 0 |
| SUFFICIENT | 1 | 0 | 0 | 0 | 8 | 0 | 0 | 0 |
| CANNOT_ANSWER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REPEAT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| WAIT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Each element on its own, using all the gaps the judge returned:

- Whole list of gaps exactly right: 78/105 = 74.3%
- Judge quotes that passed the substring check: 112/114 = 98.2%

| Element | Caught when missing | False alarm when present |
|---|---|---|
| concrete_example | 63/65 = 96.9% | 3/40 = 7.5% |
| measurable_outcome | 44/46 = 95.7% | 0/59 = 0.0% |
| personal_ownership | 56/56 = 100.0% | 12/49 = 24.5% |
| clear_scope | 61/68 = 89.7% | 4/37 = 10.8% |

## Persona check
Replies that visibly broke their key (only "I" and numbers can be checked by a script):
- Replies with a break: 11/150 = 7.3%
- personal_ownership missing: 9
- personal_ownership leaked: 2

## Follow-ups
- Targeting (asked for an element that really was missing): 89/94 = 94.7%

| Persona | Follow-ups per question | Verdict counts |
|---|---|---|
| strong_specific | 1.00 (n=8) | SUFFICIENT 5, NO_CONCRETE_EXAMPLE 4, UNCLEAR_SCOPE 3, NO_MEASURABLE_OUTCOME 1 |
| rambler | 1.25 (n=8) | NO_PERSONAL_OWNERSHIP 4, SUFFICIENT 3, NO_CONCRETE_EXAMPLE 2, NO_MEASURABLE_OUTCOME 2, UNCLEAR_SCOPE 2 |
| vague_generalist | 2.00 (n=8) | NO_CONCRETE_EXAMPLE 15, NO_MEASURABLE_OUTCOME 1 |
| bluffer | 2.00 (n=8) | NO_CONCRETE_EXAMPLE 14, NO_MEASURABLE_OUTCOME 2 |
| nervous_minimal | 1.88 (n=8) | NO_CONCRETE_EXAMPLE 12, NO_MEASURABLE_OUTCOME 4 |
| question_asker | 1.75 (n=8) | NO_CONCRETE_EXAMPLE 9, NO_MEASURABLE_OUTCOME 4, REPEAT_REQUEST 2, SUFFICIENT 1, NO_PERSONAL_OWNERSHIP 1 |
| hostile | 1.88 (n=8) | NO_CONCRETE_EXAMPLE 10, NO_PERSONAL_OWNERSHIP 5, NO_MEASURABLE_OUTCOME 1 |

## Scores
- strong: mean 3.25 (n=16)
- weak: mean 1.12 (n=24)
- mixed: mean 1.81 (n=16)
- strong_specific: mean 3.12 (n=8)
- rambler: mean 3.38 (n=8)
- vague_generalist: mean 1.12 (n=8)
- bluffer: mean 1.12 (n=8)
- nervous_minimal: mean 1.12 (n=8)
- question_asker: mean 1.62 (n=8)
- hostile: mean 2.00 (n=8)
- Strong group's mean above weak group's mean: yes

## Bluffer trap
Bluffer scores of 4 or 5: 0/8 = 0.0%

## Repeat consistency
- All 4 scores match: not measured yet of turns
- Mean max-min spread: not measured yet

## Fairness
Read against repeat consistency: a changed score may be the model's own noise.
- Score unchanged in both copies: not measured yet of turns
- Mean absolute change: not measured yet

## Judge timing
- judge() p50 1168 ms, p95 1785 ms (n=107), including any retry waits inside call_gemini

## Errored scenarios
None.
