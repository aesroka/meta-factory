# Refactoring: Improving the Design of Existing Code — Framework Summary

*Based on Martin Fowler's catalogue*

## Core Principle

Refactoring is **changing the internal structure of code without changing its external behaviour**. Small, safe steps compound into large improvements.

## The Two Hats

| Hat | Activity | Rule |
|-----|----------|------|
| **Adding Functionality** | Write new code, add tests | Don't restructure |
| **Refactoring** | Improve structure | Don't add functionality |

Never wear both hats at once.

## When to Refactor

### The Rule of Three
1. First time: Just do it
2. Second time: Wince, but do it anyway
3. Third time: Refactor

### Code Smells Trigger Refactoring

| Smell | Description | Typical Refactoring |
|-------|-------------|---------------------|
| **Duplicated Code** | Same structure in multiple places | Extract Method, Pull Up Method |
| **Long Method** | Method does too much | Extract Method, Decompose Conditional |
| **Large Class** | Class has too many responsibilities | Extract Class, Extract Subclass |
| **Long Parameter List** | Too many parameters | Introduce Parameter Object, Preserve Whole Object |
| **Feature Envy** | Method uses another class more than its own | Move Method |
| **Data Clumps** | Same data items together repeatedly | Extract Class, Introduce Parameter Object |
| **Primitive Obsession** | Overuse of primitives vs objects | Replace Data Value with Object |
| **Switch Statements** | Same switch in multiple places | Replace Conditional with Polymorphism |
| **Divergent Change** | One class changed for multiple reasons | Extract Class |
| **Shotgun Surgery** | One change requires many small changes | Move Method, Inline Class |

## Most Common Refactorings

### Extract Method
**When**: Code fragment that can be grouped together

```
Before:
  printDetails() {
    // print banner
    System.out.println("***");
    System.out.println("Customer: " + name);
    // print details
    System.out.println("Amount: " + amount);
  }

After:
  printDetails() {
    printBanner();
    printCustomerInfo();
  }
```

### Extract Class
**When**: Class doing work that should be two classes

**Signs**: Subset of features used together, subset of data used together

### Move Method
**When**: Method uses more features of another class

**Process**:
1. Copy method to target class
2. Adjust for new home
3. Redirect calls from source to target
4. Remove source method

### Replace Conditional with Polymorphism
**When**: Switch statement or chained conditionals on type

```
Before:
  switch(type) {
    case "A": return handleA();
    case "B": return handleB();
  }

After:
  interface Handler { handle(); }
  class AHandler implements Handler { ... }
  class BHandler implements Handler { ... }
```

### Introduce Parameter Object
**When**: Parameters that naturally belong together

```
Before:
  calculateFee(startDate, endDate, rate)

After:
  calculateFee(dateRange, rate)
```

## Safe Refactoring Process

1. **Ensure tests exist** — Cannot refactor safely without tests
2. **Make one small change** — Smallest possible step
3. **Run tests** — Must still pass
4. **Commit** — Create a checkpoint
5. **Repeat** — Many small steps, not one big leap

## Refactoring vs. Performance

- Refactor first for clarity
- Measure performance after
- Optimize only proven bottlenecks
- Well-structured code is easier to optimize

## Composing Methods (Priority Order)

1. **Extract Method** — Most common, most valuable
2. **Inline Method** — When indirection is pointless
3. **Replace Temp with Query** — Makes extraction easier
4. **Introduce Explaining Variable** — When expressions are complex

## Moving Features Between Objects

1. **Move Method** — Method belongs elsewhere
2. **Move Field** — Data belongs elsewhere
3. **Extract Class** — Class is too big
4. **Inline Class** — Class isn't doing enough

## Organising Data

1. **Replace Data Value with Object** — Primitive needs behaviour
2. **Replace Array with Object** — Array used as data structure
3. **Encapsulate Field** — Public field needs protection
4. **Replace Magic Number with Symbolic Constant**

## Branch by Abstraction (for Large Changes)

1. Create abstraction layer over existing code
2. Migrate clients to use abstraction
3. Create new implementation behind abstraction
4. Switch abstraction to new implementation
5. Remove old implementation

## Output for Planning

For each code smell identified:

| Location | Smell | Proposed Refactoring | Risk | Effort |
|----------|-------|---------------------|------|--------|
