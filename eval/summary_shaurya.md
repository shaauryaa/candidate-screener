# Persona evaluation

Scenarios: 7 finished, 0 errored.

## Scoring
- O1 rubric coverage: 28/28 = 100.0% of rubric dimensions (the controller visits every question, so this is high by construction)
- O3 verified-quote rate: 28/28 = 100.0%

## Judge accuracy vs the planted key
A miss can be the judge's error or a persona that didn't follow its instruction.

- Overall strict: 53/57 = 93.0%
- Overall lenient: 55/57 = 96.5%

| Persona | Strict | Lenient |
|---|---|---|
| strong_specific | 7/7 = 100.0% | 7/7 = 100.0% |
| rambler | 6/7 = 85.7% | 6/7 = 85.7% |
| vague_generalist | 8/8 = 100.0% | 8/8 = 100.0% |
| bluffer | 7/8 = 87.5% | 7/8 = 87.5% |
| nervous_minimal | 8/8 = 100.0% | 8/8 = 100.0% |
| question_asker | 9/11 = 81.8% | 11/11 = 100.0% |
| hostile | 8/8 = 100.0% | 8/8 = 100.0% |

Confusion table (rows = strict expected, columns = returned):

| Expected | NO_CONCRETE_EXAMPLE | NO_MEASURABLE_OUTCOME | NO_PERSONAL_OWNERSHIP | UNCLEAR_SCOPE | SUFFICIENT | CANNOT_ANSWER | REPEAT_REQUEST | WAIT_REQUEST |
|---|---|---|---|---|---|---|---|---|
| NO_CONCRETE_EXAMPLE | 22 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| NO_MEASURABLE_OUTCOME | 1 | 14 | 0 | 0 | 0 | 0 | 0 | 0 |
| NO_PERSONAL_OWNERSHIP | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 |
| UNCLEAR_SCOPE | 0 | 1 | 0 | 3 | 0 | 0 | 0 | 0 |
| SUFFICIENT | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| CANNOT_ANSWER | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REPEAT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| WAIT_REQUEST | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Each element on its own, using all the gaps the judge returned:

- Whole list of gaps exactly right: 44/54 = 81.5%
- Judge quotes that passed the substring check: 51/51 = 100.0%

| Element | Caught when missing | False alarm when present |
|---|---|---|
| concrete_example | 22/24 = 91.7% | 1/30 = 3.3% |
| measurable_outcome | 37/37 = 100.0% | 1/17 = 5.9% |
| personal_ownership | 31/31 = 100.0% | 4/23 = 17.4% |
| clear_scope | 35/35 = 100.0% | 2/19 = 10.5% |

## Persona check
Replies that visibly broke their key (only "I" and numbers can be checked by a script):
- Replies with a break: 4/73 = 5.5%
- personal_ownership leaked: 3
- measurable_outcome missing: 1

## Follow-ups
- Targeting (asked for an element that really was missing): 43/45 = 95.6%

| Persona | Follow-ups per question | Verdict counts |
|---|---|---|
| strong_specific | 1.25 (n=4) | NO_MEASURABLE_OUTCOME 2, NO_PERSONAL_OWNERSHIP 2, SUFFICIENT 2, NO_CONCRETE_EXAMPLE 1 |
| rambler | 1.00 (n=4) | SUFFICIENT 3, NO_MEASURABLE_OUTCOME 2, UNCLEAR_SCOPE 2 |
| vague_generalist | 1.75 (n=4) | NO_CONCRETE_EXAMPLE 6, NO_MEASURABLE_OUTCOME 2 |
| bluffer | 2.00 (n=4) | NO_CONCRETE_EXAMPLE 5, NO_MEASURABLE_OUTCOME 3 |
| nervous_minimal | 1.75 (n=4) | NO_CONCRETE_EXAMPLE 4, NO_MEASURABLE_OUTCOME 4 |
| question_asker | 1.75 (n=4) | NO_CONCRETE_EXAMPLE 4, REPEAT_REQUEST 3, NO_MEASURABLE_OUTCOME 2, NO_PERSONAL_OWNERSHIP 1, UNCLEAR_SCOPE 1 |
| hostile | 1.75 (n=4) | NO_CONCRETE_EXAMPLE 3, NO_MEASURABLE_OUTCOME 2, NO_PERSONAL_OWNERSHIP 2, SUFFICIENT 1 |

## Scores
- strong: mean 2.75 (n=8)
- weak: mean 1.08 (n=12)
- mixed: mean 1.50 (n=8)
- strong_specific: mean 3.25 (n=4)
- rambler: mean 2.25 (n=4)
- vague_generalist: mean 1.25 (n=4)
- bluffer: mean 1.00 (n=4)
- nervous_minimal: mean 1.00 (n=4)
- question_asker: mean 1.50 (n=4)
- hostile: mean 1.50 (n=4)
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
- judge() p50 1450 ms, p95 2822 ms (n=57), including any retry waits inside call_gemini

## Errored scenarios
None.
