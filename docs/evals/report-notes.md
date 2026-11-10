## What was measured

The evals test the language-model layer of a planning assistant. Given a Vietnamese chat message and a store of plans, does the model choose the right tool, send valid arguments, and leave the store in the right state? The code, not the model, does date arithmetic, computes a day's load and picks which tasks to move; the evals check that the model uses those tools and reports their results faithfully.

Three suites: v1 (50 cases of general tool use), v2 (17 cases on dates, relative deadlines, deadline clashes, long messages, priority and effort) and v3 (8 cases on the daily load check). Each case runs three times against one model (Claude Haiku 5.5) with a fixed clock. Scoring is deterministic checks on tool calls, replies and the store; there is no model acting as judge.

## How to read the numbers

With three runs per case, one run moves a case's rate by 33 points, so conclusions should rest on failure patterns that repeat, not on single figures. With the same prompt and tool catalog, v1 scored 135 of 150 on the tool rule on 10 November and 150 of 150 on 11 November. Of the 15 failures in the first run, 13 came from a scoring rule that was fixed in between (see below) and 2 did not recur.

Rates are comparable only within one scorer version. Scorer 2 added date, priority and effort checks, scorer 3 added the v3 branch, and scorer 4 changed one v1 group (details view).

## What the evals found

1. The details-view group scored 0 to 13 percent for ten days. The rule demanded a call to get_plan_detail, but get_plans already returns every task with status, note, date and effort. A manual check of all 15 replies in one run found the right facts in every one. The rule was wrong, not the model, and scorer 4 accepts either read tool.
2. The first v3 run scored 6 of 24 on the tool rule while no task was written to a day that the tool had reported over budget. The model never repeated the tool's warning sentence word for word (0 of 24), yet it relayed the totals, the tasks and the dates correctly. The specification and scorer now check the parts of the answer. Two real gaps remained and were fixed in prompt version 9: the note that hours were an estimate was dropped in two of three runs of one case, and on the confirmation turn the model sometimes sent displaced tasks through the wrong tool.
3. One v3 case measured the wrong thing: the word "deadline" in the user message triggers a different rule (a plan-wide deadline dates only the last task). Reading the failing runs found this; the case was rewritten.

## Known limitations

- Confirmation turn (v3, case V3-07): the intended path (add_subtask carrying the confirmed moves) was taken in 4 of 6 runs. The other 2 reached the same final state through reschedule_subtasks with confirm set, which skips the deadline-clash check. The confirmation flag is not proof of consent; this trade-off is accepted and recorded in D-029.
- Cases about plan-wide deadlines (P04 in v1, V2-06 in v2) have moved between 0.67 and 1.0 from run to run since prompt version 6.
- Overdue tasks are never moved automatically, count zero toward any day's load, and stay at the top of the morning digest until marked done. The 14-day simulation in docs/simulation/fortnight.md shows this.
- No live usage: the system was exercised by these evals and by a seeded simulation (10 invariants checked after every action, 437 actions over 6 seeds), not by weeks of daily use.
- Costs are estimates from token counts, not invoices; the console showed 0.37 USD for the first round of three runs on 10 November (p8-d4), against 0.37 USD estimated from their token counts.
