# KHALA ARCHITECTURE (03-architecture.md)

> **SYSTEM ROLE: LEAD ARCHITECT**
> This file defines the **Structural Laws** of the codebase. It dictates folder structures, dependency rules, and abstraction boundaries.

---

## 1. Domain-Driven Design (DDD) Layers

Khala follows a strict 4-layer architecture to ensure decoupling and testability.

### A. Pure Domain (`khala/domain/`)
- **Definition**: Core business entities and logic.
- **Rules**: 
    - **NO** external dependencies (except standard libraries or Pydantic).
    - Contains `entities.py`, `value_objects.py`, and domain `services.py`.
    - Defines **Repository Interfaces** (Protocols/ABCs) but not their implementations.

### B. Application Layer (`khala/application/`)
- **Definition**: Orchestrates domain objects to perform specific use cases.
- **Rules**:
    - Calls Domain Services and Repositories.
    - Contains `coordination/` (Orchestrators), `services/` (Cognitive services), and `verification/` (Logic gates).

### C. Infrastructure Layer (`khala/infrastructure/`)
- **Definition**: Technical implementation of repository interfaces (SurrealDB, MinIO).
- **Rules**:
    - Depends on external libraries (SurrealDB-Python, Gemini).
    - MUST implement an interface defined in the Domain layer.
    - **Forbidden**: Domain or Application layers importing directly from `infrastructure/surrealdb/client.py`.

### D. Interface Layer (`khala/interface/`)
- **Definition**: Entry points into the system (CLI, REST, Agno, MCP).

---

## 2. Abstraction & Abundance Rules (AHA & WET)

**"Duplication is far cheaper than the wrong abstraction."**

### A. The Rule of WET (Write Everything Twice)
1. **First time**: Write code specific to the use case.
2. **Second time**: Copy and paste the code. Tailor it to the new specific context.
3. **Third time**: Only NOW consider extracting it into a shared abstraction, *if and only if* the implementation logic is identical (not just the structure).

### B. The Anti-Pattern: "God Objects"
- **Forbidden**: Do not create generic "Manager" or "Handler" classes (e.g., `MemoryManager`).
- **Correct**: Name things by exactly what they do (e.g., `DecayScoringService`, `DeduplicationWorker`).

---

## 3. Colocation & "Pluginplayability"

We optimize for **deletability** and **readability**.

### A. The Isolation Test
Ask yourself: *"If I delete the folder `khala/application/services/FEATURE_X`, will the application crash in unrelated areas?"*
- If YES: You have failed. Refactor dependencies using Interfaces.

### B. Colocation Rule
- Keep related files (schemas, logic, unit tests) as close as possible.
- **Module Structure Example**:
    ```text
    khala/domain/memory/
    ├── entities.py
    ├── repository.py
    ├── services.py
    └── value_objects.py
    ```

---

## 4. Cross-Domain Communication
- **Rule**: Domain A should not directly import deep files from Domain B.
- **Mechanism**: Use **Public Interfaces/Contracts**. Domain A uses an ABC defined in Domain B.

---

## 5. System Visualization Domain
The **Khala Console** (`external/khala-console`) is the visualization port of the system.
- It interacts with the core via the REST or MCP interfaces.
- **Architecture**: React/Vite/Tailwind following a Component-Driven Development (CDD) pattern.
