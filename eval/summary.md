# Persona evaluation

Scenarios: 7 finished, 0 errored.

## Scoring
- O1 rubric coverage: 28/28 = 100.0% of rubric dimensions (the controller visits every question, so this is high by construction)
- O3 verified-quote rate: 28/28 = 100.0%

## Judge accuracy vs the planted key
A miss can be the judge's error or a persona that didn't follow its instruction.

- Overall strict: 49/54 = 90.7%
- Overall lenient: 51/54 = 94.4%

| Persona | Strict | Lenient |
|---|---|---|
| strong_specific | 8/8 = 100.0% | 8/8 = 100.0% |
| rambler | 6/6 = 100.0% | 6/6 = 100.0% |
| vague_generalist | 7/8 = 87.5% | 7/8 = 87.5% |
| bluffer | 8/8 = 100.0% | 8/8 = 100.0% |
| nervous_minimal | 8/8 = 100.0% | 8/8 = 100.0% |
| question_asker | 7/8 = 87.5% | 7/8 = 87.5% |
| hostile | 5/8 = 62.5% | 7/8 = 87.5% |

Confusion table (rows = strict expected, columns = returned):

| Expected | NO_CONCRETE_EXAMPLE | NO_MEASURABLE_OUTCOME | NO_PERSONAL_OWNERSHIP | UNCLEAR_SCOPE | SUFFICIENT | CANNOT_ANSWER | REPEAT_REQUEST | WAIT_REQUEST |
|---|---|---|---|---|---|---|---|---|
| NO_CONCRETE_EXAMPLE | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| NO_MEASURABLE_OUTCOME | 1 | 4 | 2 | 0 | 0 | 0 | 0 | 0 |
| NO_PERSONAL_OWNERSHIP | 1 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| UNCLEAR_SCOPE | 0 | 0 | 0 | 3 | 1 | 0 | 0 | 0 |
| SUFFICIENT | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 |
| CANNOT_ANSWER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REPEAT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| WAIT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Each element on its own, using all the gaps the judge returned:

- Whole list of gaps exactly right: 40/53 = 75.5%
- Judge quotes that passed the substring check: 62/62 = 100.0%

| Element | Caught when missing | False alarm when present |
|---|---|---|
| concrete_example | 33/33 = 100.0% | 2/20 = 10.0% |
| measurable_outcome | 13/15 = 86.7% | 0/38 = 0.0% |
| personal_ownership | 34/34 = 100.0% | 0/19 = 0.0% |
| clear_scope | 27/34 = 79.4% | 2/19 = 10.5% |

## Persona check
Replies that visibly broke their key (only "I" and numbers can be checked by a script):
- Replies with a break: 2/74 = 2.7%
- personal_ownership leaked: 2

## Follow-ups
- Targeting (asked for an element that really was missing): 44/46 = 95.7%

| Persona | Follow-ups per question | Verdict counts |
|---|---|---|
| strong_specific | 1.50 (n=4) | UNCLEAR_SCOPE 3, NO_CONCRETE_EXAMPLE 3, SUFFICIENT 2 |
| rambler | 1.00 (n=4) | SUFFICIENT 2, NO_PERSONAL_OWNERSHIP 2, NO_CONCRETE_EXAMPLE 1, NO_MEASURABLE_OUTCOME 1 |
| vague_generalist | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 7, NO_MEASURABLE_OUTCOME 1 |
| bluffer | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 8 |
| nervous_minimal | 1.75 (n=4) | NO_CONCRETE_EXAMPLE 8 |
| question_asker | 1.50 (n=4) | NO_CONCRETE_EXAMPLE 4, NO_MEASURABLE_OUTCOME 2, SUFFICIENT 1, REPEAT_REQUEST 1 |
| hostile | 1.75 (n=4) | NO_CONCRETE_EXAMPLE 4, NO_PERSONAL_OWNERSHIP 4 |

## Scores
- strong: mean 3.12 (n=8)
- weak: mean 1.08 (n=12)
- mixed: mean 1.88 (n=8)
- strong_specific: mean 3.25 (n=4)
- rambler: mean 3.00 (n=4)
- vague_generalist: mean 1.25 (n=4)
- bluffer: mean 1.00 (n=4)
- nervous_minimal: mean 1.00 (n=4)
- question_asker: mean 1.75 (n=4)
- hostile: mean 2.00 (n=4)
- Strong group's mean above weak group's mean: yes

## Bluffer trap
Bluffer scores of 4 or 5: 0/4 = 0.0%

## Repeat consistency
- All 4 scores match: not measured yet of turns
- Mean max-min spread: not measured yet

## Fairness
Read against repeat consistency: a changed score may be the model's own noise.
- Score unchanged in both copies: not measured yet of turns
- Mean absolute change: not measured yet

## Judge timing
- judge() p50 1229 ms, p95 5960 ms (n=54), including any retry waits inside call_gemini

## Errored scenarios
None.
