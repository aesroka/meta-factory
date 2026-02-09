# Software Estimation — Framework Summary

*Based on Steve McConnell's techniques*

## Core Principle

All estimates are **uncertain**. Good estimation acknowledges uncertainty explicitly and communicates ranges, not points.

## The Cone of Uncertainty

Estimate accuracy improves as project progresses:

| Phase | Low Multiplier | High Multiplier | Range |
|-------|---------------|-----------------|-------|
| Initial Concept | 0.25x | 4.0x | 16x |
| Approved Product Definition | 0.50x | 2.0x | 4x |
| Requirements Complete | 0.67x | 1.5x | 2.25x |
| UI Design Complete | 0.80x | 1.25x | 1.5x |
| Detailed Design Complete | 0.90x | 1.10x | 1.2x |
| Software Complete | 1.0x | 1.0x | 1x |

**Key Insight**: Early estimates MUST be ranges. Point estimates early on are misleading.

## Estimation vs. Target vs. Commitment

| Term | Definition | Example |
|------|------------|---------|
| **Estimate** | Prediction based on analysis | "This will probably take 3-5 months" |
| **Target** | Business goal | "We need it by March" |
| **Commitment** | Promise to deliver | "We will deliver by March 15" |

**Critical Rule**: Never let targets contaminate estimates. Estimate first, then negotiate commitments.

## PERT Estimation

Three-point estimation for individual tasks:

| Value | Description | Symbol |
|-------|-------------|--------|
| Optimistic | Everything goes right | O |
| Likely | Most probable outcome | M |
| Pessimistic | Things go wrong | P |

### PERT Formulas

```
Expected Value (E) = (O + 4M + P) / 6
Standard Deviation (SD) = (P - O) / 6
```

### Combining PERT Estimates

For multiple tasks:
```
Total Expected = Sum of individual E values
Total SD = √(sum of individual SD²)
```

### Confidence Intervals

| Confidence | Range |
|------------|-------|
| 68% | E ± 1 SD |
| 90% | E ± 1.645 SD |
| 95% | E ± 2 SD |
| 99% | E ± 3 SD |

## Estimation by Decomposition

Break work into smaller pieces:
1. Identify components/tasks
2. Estimate each piece
3. Add integration/overhead (typically 10-30%)
4. Apply uncertainty range

**Rule of Thumb**: Decompose until each piece is < 2 days of work.

## Reference Class Forecasting

Use historical data from similar projects:

1. Identify reference class (similar past projects)
2. Collect actual duration/effort data
3. Use distribution, not average
4. Position your project within the class

### Example Reference Class Data

| Metric | Value |
|--------|-------|
| Projects in class | 15 |
| Median duration | 6 months |
| P10 (optimistic) | 4 months |
| P90 (pessimistic) | 10 months |

## Common Estimation Errors

### Planning Fallacy
People underestimate their own tasks while accurately estimating others'.

**Fix**: Use reference class data, not intuition.

### Anchoring
First number mentioned biases all subsequent estimates.

**Fix**: Estimate independently before discussing.

### Selective Memory
Remembering successes, forgetting failures.

**Fix**: Use documented project history.

### Precision vs. Accuracy
Detailed estimates feel more accurate but aren't.

**Fix**: Express appropriate uncertainty.

## Effort vs. Duration

Effort (person-hours) ≠ Duration (calendar time)

```
Duration = Effort / (People × Productivity Factor)
```

| Team Size | Productivity Factor |
|-----------|---------------------|
| 1 person | 1.0 |
| 2 people | 0.9 |
| 4 people | 0.8 |
| 8 people | 0.65 |

**Brooks's Law**: Adding people to a late project makes it later.

## Risk-Adjusted Estimates

Multiply base estimate by risk factor:

| Risk Level | Multiplier |
|------------|------------|
| Low (proven tech, experienced team) | 1.0 |
| Medium (some unknowns) | 1.25 |
| High (new tech, new domain) | 1.5-2.0 |
| Very High (research-like) | 2.0-4.0 |

## Presenting Estimates

### Do:
- Present ranges, not points
- State assumptions explicitly
- Identify risks and their impact
- Note confidence level
- Include what's in and out of scope

### Don't:
- Give single-point estimates
- Pad secretly (be transparent)
- Commit to targets you can't meet
- Ignore uncertainty

## Estimate Template

```
Task: [Description]
Optimistic: [X hours] - if everything goes perfectly
Likely: [Y hours] - realistic expectation
Pessimistic: [Z hours] - if significant problems occur
Expected: [E hours] (PERT calculation)
Standard Deviation: [SD hours]
90% Confidence Range: [E-1.645SD to E+1.645SD hours]
Assumptions: [List]
Risks: [List with impact]
```

## Output for Proposals

| Task | O | M | P | Expected | SD | 90% Range |
|------|---|---|---|----------|----|-----------|
