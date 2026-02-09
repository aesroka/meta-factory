# C4 Model — Framework Summary

*Based on Simon Brown's methodology*

## Core Principle

Visualise software architecture at **multiple levels of abstraction**, like zooming in on a map. Different audiences need different levels of detail.

## The Four Levels

```
Level 1: System Context
         ↓ zoom in
Level 2: Container
         ↓ zoom in
Level 3: Component
         ↓ zoom in
Level 4: Code
```

## Level 1: System Context

**Audience**: Everyone (technical and non-technical)

**Shows**: Your system as a box + the people/systems it interacts with

**Purpose**: "Here's the big picture of what we're building and who uses it"

### Elements
- **Your System** (single box)
- **Users/Actors** (people or personas)
- **External Systems** (systems you interact with)

### Example
```
[Customer] → [E-Commerce System] → [Payment Provider]
                    ↓
              [Shipping API]
```

### Questions It Answers
- What system are we building?
- Who uses it?
- What external systems does it depend on?

## Level 2: Container

**Audience**: Technical people (developers, ops, architects)

**Shows**: The high-level tech choices (applications, data stores, etc.)

**Purpose**: "Here are the major building blocks and how they communicate"

### Elements
- **Web Application** (e.g., React SPA)
- **API Application** (e.g., Node.js API)
- **Database** (e.g., PostgreSQL)
- **Message Queue** (e.g., RabbitMQ)
- **File Storage** (e.g., S3)

### Example
```
[Web App] --REST--> [API Server] --SQL--> [Database]
                         |
                    [Message Queue]
                         |
                   [Background Worker]
```

### Questions It Answers
- What are the major applications/services?
- What technologies are used?
- How do they communicate?
- Where is data stored?

## Level 3: Component

**Audience**: Developers working on the system

**Shows**: Components/modules within a container

**Purpose**: "Here's how this container is organised internally"

### Elements
- **Controllers** (handle HTTP requests)
- **Services** (business logic)
- **Repositories** (data access)
- **External Adapters** (third-party integrations)

### Example
```
[OrderController] → [OrderService] → [OrderRepository]
                          ↓
                   [PaymentAdapter]
```

### Questions It Answers
- What are the major code components?
- What are their responsibilities?
- How do they interact?

## Level 4: Code

**Audience**: Developers working on specific features

**Shows**: Classes, interfaces, modules (UML-style)

**Purpose**: Detailed design documentation

**Note**: Often not needed — code itself is the documentation at this level.

## Notation Guidelines

### Box Styling

| Element Type | Shape | Color (convention) |
|--------------|-------|-------------------|
| Person | Stick figure or named shape | Blue |
| Software System (yours) | Box | Blue |
| Software System (external) | Box | Grey |
| Container | Box | Blue |
| Component | Box | Blue |
| Database | Cylinder | Blue |

### Relationships

```
[Source] --"action"--> [Destination]
         ^label describes the interaction
```

### Labels Should Include
- What data flows
- What protocol (REST, gRPC, SQL)
- Direction of flow

### Good Label Examples
- "Sends order events via RabbitMQ"
- "Reads/writes data via JDBC"
- "Makes API calls via HTTPS/JSON"

## Key Principles

### 1. Abstractions First
Define abstractions before drawing diagrams:
- What containers exist?
- What components are in each?
- What are the responsibilities?

### 2. Keep It Simple
- Use consistent notation
- Don't overcrowd diagrams
- One diagram per level per scope

### 3. Title + Description
Every diagram needs:
- Clear title
- Brief description
- Legend if needed

### 4. Diagram Is a View
Diagrams are **views** of the model. The model (abstractions, relationships) is the source of truth.

## Creating C4 Diagrams

### 1. Start with Context
- List all users/actors
- List all external systems
- Draw your system in the middle

### 2. Decompose into Containers
- What are the deployable units?
- What technologies?
- How do they communicate?

### 3. Decompose into Components (if needed)
- What are the major responsibilities?
- What modules/packages/namespaces?
- How do they depend on each other?

## Tools

- **Structurizr** (Brown's tool)
- **PlantUML** with C4 extension
- **Mermaid** with C4 extension
- **Draw.io** with C4 shapes

## PlantUML C4 Example

```plantuml
@startuml
!include C4_Container.puml

Person(user, "Customer")
System_Boundary(c1, "E-Commerce") {
  Container(web, "Web App", "React")
  Container(api, "API", "Node.js")
  ContainerDb(db, "Database", "PostgreSQL")
}
System_Ext(payment, "Payment Provider")

Rel(user, web, "Uses")
Rel(web, api, "Calls", "REST/HTTPS")
Rel(api, db, "Reads/Writes")
Rel(api, payment, "Sends payments")
@enduml
```

## Output for Documentation

For each level, produce:

| Level | Diagram | Description | Key Decisions |
|-------|---------|-------------|---------------|
| Context | [Mermaid/PlantUML] | System boundaries | External integrations |
| Container | [Mermaid/PlantUML] | Technology choices | Architecture style |
| Component | [Mermaid/PlantUML] | Module structure | Internal patterns |
