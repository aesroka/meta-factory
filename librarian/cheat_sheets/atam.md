# ATAM: Architecture Tradeoff Analysis Method — Framework Summary

## Core Principle

Architecture decisions involve **tradeoffs**. ATAM makes these tradeoffs explicit by analysing how architecture decisions affect quality attributes.

## When to Use ATAM

- Early in development (before major implementation)
- Major architectural decisions pending
- Multiple stakeholders with different concerns
- Quality attributes are critical to success

## The Quality Attributes

| Attribute | Concerns |
|-----------|----------|
| **Performance** | Latency, throughput, capacity |
| **Availability** | Uptime, MTTR, fault tolerance |
| **Security** | Confidentiality, integrity, authentication |
| **Modifiability** | Change cost, coupling, cohesion |
| **Scalability** | Load handling, horizontal/vertical scaling |
| **Testability** | Observability, controllability |
| **Usability** | User experience, learnability |
| **Interoperability** | Integration with other systems |

## The Utility Tree

Central artifact for prioritising quality attribute scenarios.

### Structure

```
Quality Attributes
├── Performance
│   ├── (H,H) System responds to API calls within 200ms under peak load
│   └── (M,L) Batch jobs complete within 4-hour window
├── Security
│   ├── (H,M) All data encrypted at rest and in transit
│   └── (H,H) Authentication handles 10K concurrent sessions
└── Modifiability
    └── (M,M) New payment provider integrable within 2 weeks
```

### Priority Matrix

| Importance \ Difficulty | High | Medium | Low |
|------------------------|------|--------|-----|
| **High** | H,H (Focus) | H,M | H,L |
| **Medium** | M,H | M,M | M,L |
| **Low** | L,H | L,M | L,L |

**Focus on (H,H)**: High importance + High difficulty = Architecture drivers

## Quality Attribute Scenario Template

A complete scenario has six parts:

| Part | Description | Example |
|------|-------------|---------|
| **Source** | Who/what generates stimulus | End user |
| **Stimulus** | Event that affects system | Submits order |
| **Artifact** | What part of system is affected | Order service |
| **Environment** | Conditions during stimulus | Peak load (1000 concurrent users) |
| **Response** | How system should respond | Order processed |
| **Measure** | How to evaluate response | Within 2 seconds, 99.9% success |

### Example Scenario

> "When an **end user** submits an **order** to the **order service** during **peak load**, the order is **processed and confirmed** within **2 seconds with 99.9% success rate**."

## Sensitivity and Tradeoff Points

### Sensitivity Point
An architectural decision that affects ONE quality attribute.

Example: "Caching layer size affects performance response time."

### Tradeoff Point
An architectural decision that affects MULTIPLE quality attributes in DIFFERENT directions.

Example: "Adding encryption improves security but degrades performance."

## Common Tradeoffs

| Decision | Improves | Degrades |
|----------|----------|----------|
| Caching | Performance | Consistency, Memory usage |
| Encryption | Security | Performance |
| Microservices | Modifiability, Scalability | Complexity, Performance (network) |
| Synchronous calls | Simplicity | Availability, Scalability |
| Redundancy | Availability | Cost, Consistency |
| Denormalisation | Read performance | Write performance, Consistency |

## Risk Identification

During analysis, identify:

| Risk Type | Description |
|-----------|-------------|
| **Technical Risk** | Architectural approach may not work |
| **Schedule Risk** | May take longer than expected |
| **Cost Risk** | May cost more than budgeted |
| **Quality Risk** | May not meet quality requirements |

## ATAM Process (Simplified)

1. **Present Architecture** — Describe the proposed architecture
2. **Identify Quality Attributes** — What matters to stakeholders?
3. **Build Utility Tree** — Prioritise (importance × difficulty)
4. **Analyse Architectural Approaches** — How does architecture address each scenario?
5. **Identify Sensitivity Points** — What affects single attributes?
6. **Identify Tradeoffs** — What affects multiple attributes?
7. **Document Risks** — What could go wrong?

## Output Template

### Quality Attribute Scenario

```
ID: QA-001
Attribute: Performance
Scenario: 1000 users query dashboard simultaneously
Priority: (H, H)
Response Measure: 95th percentile < 500ms
```

### Architectural Decision

```
ID: AD-001
Decision: Use Redis cache for dashboard queries
Rationale: Addresses QA-001 (performance under load)
Tradeoffs: Increased complexity, potential stale data
Sensitivity: Cache TTL directly affects response time
Risks: Cache invalidation complexity
```

## Anti-Patterns

- **Quality Attribute Soup**: Listing attributes without scenarios
- **Missing Measures**: Scenarios without measurable responses
- **Ignoring Tradeoffs**: Pretending decisions have no downsides
- **Over-Architecture**: Solving problems that don't exist (L,L scenarios)
