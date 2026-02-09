# Working Effectively with Legacy Code — Framework Summary

*Based on Michael Feathers' techniques*

## Core Principle

Legacy code is **code without tests**. The goal is to get it under test safely, then refactor incrementally.

## The Legacy Code Dilemma

> "When we change code, we should have tests in place. To put tests in place, we often have to change code."

**Resolution**: Use safe, mechanical techniques that break dependencies with minimal risk.

## The Seam Model

A **seam** is a place where you can alter behaviour without editing the code itself.

### Types of Seams

| Seam Type | Description | Example |
|-----------|-------------|---------|
| **Object Seam** | Override method in subclass | Create testing subclass |
| **Link Seam** | Replace dependencies at link time | Swap library implementations |
| **Preprocessor Seam** | Use macros/conditions | Feature flags, conditional compilation |

### Enabling Points

For each seam, the **enabling point** is where you choose which behaviour runs.

## The Legacy Code Change Algorithm

1. **Identify change points** — Where does the code need to change?
2. **Find test points** — Where can you observe behaviour?
3. **Break dependencies** — Use seams to isolate the code
4. **Write tests** — Characterisation tests first
5. **Make changes** — Now safe to refactor

## Dependency-Breaking Techniques

### For Constructors

| Technique | When to Use |
|-----------|-------------|
| **Extract Interface** | Need to mock a dependency |
| **Parameterize Constructor** | Constructor creates hard-coded dependencies |
| **Extract and Override Factory Method** | Complex object creation in constructor |
| **Supersede Instance Variable** | Cannot modify constructor |

### For Methods

| Technique | When to Use |
|-----------|-------------|
| **Sprout Method** | Need to add new behaviour without changing existing code |
| **Sprout Class** | New functionality is substantial |
| **Wrap Method** | Need to add behaviour before/after existing method |
| **Wrap Class** | Need to add behaviour to an entire class |

## Sprout vs. Wrap

### Sprout Method
```
Original:
  doSomething()

After Sprouting:
  doSomething() {
    newBehaviour()  // Added
    originalCode()  // Unchanged
  }
```

### Wrap Method
```
Original:
  doSomething()

After Wrapping:
  doSomething() {
    beforeHook()    // New
    doSomethingOriginal()  // Renamed
    afterHook()     // New
  }
```

## Characterisation Tests

**Purpose**: Document what the code actually does (not what it should do).

**Process**:
1. Write a test that fails
2. Adjust the expected value to match actual behaviour
3. Repeat until behaviour is captured
4. Now you have a safety net

**Rule**: Characterisation tests should **pass**, not fail. They capture current behaviour.

## The Scratch Refactoring Technique

1. Take a copy of the code
2. Refactor aggressively to understand it
3. Throw it away
4. Now write tests for the original
5. Apply learnings properly

## Risk Assessment for Changes

| Risk Factor | Questions |
|-------------|-----------|
| **Coupling** | How many places call this code? |
| **Complexity** | What's the cyclomatic complexity? |
| **Coverage** | Are there existing tests? |
| **Change Frequency** | How often does this area change? |

## Test Order Priority

1. **High coupling, high change frequency** — Most ROI for tests
2. **High complexity, no coverage** — Highest risk
3. **Stable, well-tested code** — Leave alone

## Seam Identification Checklist

For any code block you need to test:

- [ ] Can I create a testing subclass? (Object seam)
- [ ] Can I pass the dependency as a parameter?
- [ ] Can I extract an interface?
- [ ] Can I use a factory method?
- [ ] Can I wrap the problematic code?
- [ ] Can I sprout new functionality separately?

## Output for Architecture Planning

Document each identified seam:

| Location | Seam Type | Risk Level | Test Strategy | Remediation |
|----------|-----------|------------|---------------|-------------|
