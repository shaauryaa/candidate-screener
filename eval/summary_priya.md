# Persona evaluation

Scenarios: 7 finished, 0 errored.

## Scoring
- O1 rubric coverage: 28/28 = 100.0% of rubric dimensions (the controller visits every question, so this is high by construction)
- O3 verified-quote rate: 28/28 = 100.0%

## Judge accuracy vs the planted key
A miss can be the judge's error or a persona that didn't follow its instruction.

- Overall strict: 50/53 = 94.3%
- Overall lenient: 52/53 = 98.1%

| Persona | Strict | Lenient |
|---|---|---|
| strong_specific | 5/5 = 100.0% | 5/5 = 100.0% |
| rambler | 7/7 = 100.0% | 7/7 = 100.0% |
| vague_generalist | 8/8 = 100.0% | 8/8 = 100.0% |
| bluffer | 8/8 = 100.0% | 8/8 = 100.0% |
| nervous_minimal | 6/8 = 75.0% | 8/8 = 100.0% |
| question_asker | 9/9 = 100.0% | 9/9 = 100.0% |
| hostile | 7/8 = 87.5% | 7/8 = 87.5% |

Confusion table (rows = strict expected, columns = returned):

| Expected | NO_CONCRETE_EXAMPLE | NO_MEASURABLE_OUTCOME | NO_PERSONAL_OWNERSHIP | UNCLEAR_SCOPE | SUFFICIENT | CANNOT_ANSWER | REPEAT_REQUEST | WAIT_REQUEST |
|---|---|---|---|---|---|---|---|---|
| NO_CONCRETE_EXAMPLE | 30 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| NO_MEASURABLE_OUTCOME | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| NO_PERSONAL_OWNERSHIP | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| UNCLEAR_SCOPE | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| SUFFICIENT | 1 | 0 | 0 | 0 | 4 | 0 | 0 | 0 |
| CANNOT_ANSWER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REPEAT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| WAIT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Each element on its own, using all the gaps the judge returned:

- Whole list of gaps exactly right: 38/52 = 73.1%
- Judge quotes that passed the substring check: 50/52 = 96.2%

| Element | Caught when missing | False alarm when present |
|---|---|---|
| concrete_example | 30/32 = 93.8% | 1/20 = 5.0% |
| measurable_outcome | 31/31 = 100.0% | 0/21 = 0.0% |
| personal_ownership | 22/22 = 100.0% | 12/30 = 40.0% |
| clear_scope | 34/34 = 100.0% | 2/18 = 11.1% |

## Persona check
Replies that visibly broke their key (only "I" and numbers can be checked by a script):
- Replies with a break: 9/76 = 11.8%
- personal_ownership missing: 9

## Follow-ups
- Targeting (asked for an element that really was missing): 45/48 = 93.8%

| Persona | Follow-ups per question | Verdict counts |
|---|---|---|
| strong_specific | 0.50 (n=4) | SUFFICIENT 3, NO_CONCRETE_EXAMPLE 1, NO_MEASURABLE_OUTCOME 1 |
| rambler | 1.50 (n=4) | NO_PERSONAL_OWNERSHIP 2, UNCLEAR_SCOPE 2, NO_CONCRETE_EXAMPLE 1, NO_MEASURABLE_OUTCOME 1, SUFFICIENT 1 |
| vague_generalist | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 8 |
| bluffer | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 6, NO_MEASURABLE_OUTCOME 2 |
| nervous_minimal | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 4, NO_MEASURABLE_OUTCOME 4 |
| question_asker | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 5, NO_MEASURABLE_OUTCOME 2, NO_PERSONAL_OWNERSHIP 1, REPEAT_REQUEST 1 |
| hostile | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 6, NO_PERSONAL_OWNERSHIP 1, NO_MEASURABLE_OUTCOME 1 |

## Scores
- strong: mean 3.38 (n=8)
- weak: mean 1.17 (n=12)
- mixed: mean 1.75 (n=8)
- strong_specific: mean 3.00 (n=4)
- rambler: mean 3.75 (n=4)
- vague_generalist: mean 1.00 (n=4)
- bluffer: mean 1.25 (n=4)
- nervous_minimal: mean 1.25 (n=4)
- question_asker: mean 1.50 (n=4)
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
- judge() p50 1164 ms, p95 1507 ms (n=53), including any retry waits inside call_gemini

## Errored scenarios
None.
