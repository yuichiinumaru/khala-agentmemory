Here is the draft for **`02-architecture.md`**.

This file acts as the **Lead Software Architect**. It strictly defines **where** code lives, **how** modules communicate, and prevents the agent from creating "spaghetti code" or over-engineered abstractions.

-----

# 02-architecture.md

> **SYSTEM ROLE: LEAD ARCHITECT**
> This file defines the **Structural Laws** of the codebase. It dictates folder structures, dependency rules, and abstraction boundaries.
> **Consult this file when creating new files, folders, or refactoring code structure.**

-----

## 1\. The Separation of Concerns: Modules vs. Components

You must strictly distinguish between **Business Logic (Modules)** and **Interface (Components)**.

### A. Modules (The "What" & "Where")

  * **Definition:** High-level vertical slices of the application based on **Business Domains** (DDD).
  * **Location:** `src/modules/`, `src/features/`, or `src/domains/`.
  * **Characteristics:**
      * Contains specific business logic (e.g., "Calculate Tax", "Approve User").
      * **High Cohesion:** Everything related to the feature stays together.
      * **Stateful:** Aware of the application state and database.

### B. Components (The "How")

  * **Definition:** Low-level horizontal building blocks.
  * **Location:** `src/components/`, `src/ui/`.
  * **Characteristics:**
      * **Dumb & Pure:** They receive data via props/arguments and emit events. They do **not** fetch data themselves.
      * **Reusable:** A `Button` component must work in the `Auth` module AND the `Billing` module.
      * **Forbidden:** Components strictly **CANNOT** import from Modules. They must remain ignorant of business logic.

-----

## 2\. The "Pluginplayability" Protocol (Low Coupling)

Our goal is an architecture where features can be added or removed like plugins without breaking the core system.

### A. The Isolation Test

**Before finalizing a new module, ask:**

> *"If I delete the folder `src/modules/FEATURE_X`, will the application crash in unrelated areas?"*

  * **If YES:** You have failed. Refactor dependencies.
  * **If NO (except for main configuration/routing):** You have succeeded.

### B. Cross-Module Communication

  * **Rule:** Module A should not directly import deep files from Module B.
  * **Mechanism:**
      * Use **Public Interfaces/Contracts** exported from the module root (`index.ts`).
      * Prefer **Events/Signals** for loose coupling (e.g., `Auth` emits `UserLoggedIn`, `Billing` listens to it).

-----

## 3\. The AHA Principle (Avoid Hasty Abstractions)

**"Duplication is far cheaper than the wrong abstraction."**

### A. The Rule of WET (Write Everything Twice)

  * **Do not** create a "Shared" or "Common" utility/component just because two pieces of code look similar.
  * **Directive:**
    1.  **First time:** Write the code specific to the use case.
    2.  **Second time:** Copy and paste the code (WET). Tailor it to the new specific context.
    3.  **Third time:** Only **NOW** should you consider extracting it into a shared abstraction, *if and only if* the implementation logic is identical (not just the structure).

### B. The Anti-Pattern: "God Objects"

  * **Forbidden:** Do not create generic "Manager" or "Handler" classes (e.g., `DataManager`, `AppHandler`). These are vague and attract unrelated logic like magnets.
  * **Correct:** Name things by exactly what they do (e.g., `InvoicePdfGenerator`, `UserPasswordHasher`).

-----

## 4\. Colocation & Directory Structure

We optimize for **deletability** and **readability**.

### A. Colocation Rule

  * **Directive:** Keep related files as close as possible.
  * **Structure:**
      * *Bad (Layered):* `src/controllers/user.ts`, `src/services/user.ts`, `src/tests/user.test.ts`
      * *Good (Modular):*
        ```text
        src/modules/user/
        ├── UserProfile.tsx
        ├── useUser.ts
        ├── userService.ts
        └── user.test.ts
        ```
  * **Reasoning:** If you need to delete the "User" feature, you delete **one folder**, not five files across the entire tree.

### B. The "Barrel" Warning (Index files)

  * **Rule:** Use `index.ts` files **ONLY** to define the public API of a module.
  * **Warning:** Do not chain exports blindly (`export * from './everything'`). This causes circular dependencies that confuse AI agents and bundlers. Be explicit (`export { User } from './User'`).

-----


## Architecture Diagram (Conceptual)

```mermaid

```

## System Workflow (Solution Overview)

```mermaid

```


> **END OF ARCHITECTURE LAWS.**
> *Proceed to `03-coding.md` for implementation details.*