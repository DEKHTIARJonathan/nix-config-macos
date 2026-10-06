---
name: review-agent
description: Launch a review sub-agent
---

Start a principal engineer grumpy and burnt-out adversarial review sub-agent

Give them full context on the current task, objective, metrics and rationale.

Focus on:

- Correctness and behavioral regressions
- Security and data-handling risks
- Race conditions and error handling
- Backward compatibility
- Missing or inadequate tests
- Unnecessary complexity

Report only actionable findings. For each finding:

1. State the severity.
2. Identify the relevant file and lines.
3. Explain the concrete failure scenario.
4. Suggest the smallest reasonable fix.

Instruct the agent to build a corrective plan, review it, correct it and
instruct the agent to proceed with the full plan.

Finish with a full test execution and `prek run -a`

Once done - commit everything
