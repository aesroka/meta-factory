# Enterprise Integration Patterns — Framework Summary

*Based on Hohpe & Woolf*

## Core Principle

Integration is hard because systems are different. Messaging provides **loose coupling** and **asynchronous communication** that respects system boundaries.

## The Four Integration Styles

| Style | Description | Coupling | Use When |
|-------|-------------|----------|----------|
| **File Transfer** | Systems exchange files | Low | Batch processes, different schedules |
| **Shared Database** | Systems share a database | High | Simple, same platform, careful design |
| **Remote Procedure Invocation** | Systems call each other (RPC/REST) | Medium-High | Real-time, synchronous needs |
| **Messaging** | Systems exchange messages | Low | Async, reliability, flexibility needed |

## Messaging System Components

```
Sender → Channel → Receiver
           ↑
        Message
```

### Message
- **Header**: Metadata (id, timestamp, correlation, routing)
- **Body**: Payload (command, document, event)

### Channel
- **Point-to-Point**: One sender, one receiver
- **Publish-Subscribe**: One sender, many receivers

### Endpoints
- **Message Endpoint**: Connects application to messaging system
- **Polling Consumer**: Pulls messages
- **Event-Driven Consumer**: Reacts to message arrival

## Message Types

| Type | Purpose | Example |
|------|---------|---------|
| **Command Message** | Invoke procedure on receiver | "ProcessOrder" |
| **Document Message** | Transfer data | Order details |
| **Event Message** | Notify of occurrence | "OrderPlaced" |
| **Request-Reply** | Two-way conversation | Query → Response |

## Essential Patterns

### Message Router
Decouples sender from receivers by determining message destination.

```
Message → [Router] → Destination A
                  → Destination B
```

### Content-Based Router
Routes based on message content.

### Message Filter
Removes unwanted messages.

### Splitter
Breaks composite message into parts.

### Aggregator
Combines related messages into one.

### Scatter-Gather
Broadcasts to recipients, aggregates responses.

```
Request → [Scatter] → Receiver 1 →
                   → Receiver 2 → [Gather] → Combined Response
```

## Message Transformation

### Message Translator
Converts between formats.

### Envelope Wrapper
Wraps message for transmission, unwraps on receipt.

### Content Enricher
Adds data from external source.

### Content Filter
Removes unneeded data.

### Normalizer
Converts different formats to common format.

## Messaging Endpoints

### Messaging Gateway
Encapsulates messaging access; application doesn't know about messaging.

### Service Activator
Connects service to messaging system.

### Transactional Client
Ensures transactional message handling.

### Competing Consumers
Multiple consumers on same channel for scalability.

### Message Dispatcher
Routes messages to different handlers based on type.

## System Management

### Control Bus
Manages/monitors distributed system.

### Detour
Inserts additional steps for testing/debugging.

### Wire Tap
Inspects messages passing through.

### Message Store
Logs messages for auditing/replay.

### Dead Letter Channel
Handles messages that can't be delivered.

## Pattern Selection Guide

| Need | Pattern |
|------|---------|
| Parallel processing | Competing Consumers |
| Format differences | Message Translator + Normalizer |
| Conditional routing | Content-Based Router |
| Broadcast + collect | Scatter-Gather |
| Break apart batches | Splitter |
| Combine responses | Aggregator |
| Add missing data | Content Enricher |
| Audit trail | Wire Tap + Message Store |
| Handle failures | Dead Letter Channel |
| Scale consumers | Competing Consumers |

## Correlation

When using Request-Reply, use **Correlation Identifier** to match requests with responses:

```
Request: { correlationId: "abc123", ... }
Response: { correlationId: "abc123", ... }
```

## Anti-Patterns to Avoid

- **Chatty Integration**: Too many small messages
- **Giant Messages**: Messages too large to process
- **Missing Correlation**: Can't match requests/responses
- **No Dead Letter Handling**: Lost messages
- **Synchronous Mindset**: Blocking on async systems

## Output for Architecture Decisions

| Integration Point | Pattern | Rationale | Failure Mode |
|-------------------|---------|-----------|--------------|
