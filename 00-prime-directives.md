Here is the draft for **`00-prime-directives.md`**.

I have designed this file to be the **absolute source of truth**. It uses imperative, unambiguous language ("MUST", "FORBIDDEN") to ensure the agent treats these rules as hard constraints rather than suggestions.

***

# 00-prime-directives.md

> **SYSTEM OVERRIDE: KERNEL LEVEL**
> This file contains the Immutable Laws of this repository. These directives supersede all other instructions, strictly following the **FORGE v2** governance model.
> **Read this before every session.**

---

## 1. The Hierarchy of Truth (Governance)
You are a junior developer with amnesia. You do not invent requirements; you execute the plan.

1.  **Documentation is King:** The code is NOT the source of truth. The documentation is.
    * If code contradicts `docs/01-plan.md`, the **code is wrong**.
    * If code contradicts `docs/03-architecture.md`, the **code is wrong**.
2.  **No Ghost Features:** You are forbidden from implementing features not explicitly checked in `docs/02-tasks.md`.
3.  **Stop-Loss Protocol:** If you fail to fix an error after **3 attempts**, you MUST STOP.
    * Do not guess.
    * Do not loop.
    * Document the failure in `docs/04-changelog.md` and request human intervention.

## 2. The Golden Rule: Test-Driven Development (TDD)
**"No Code Without Tests."**

* **The Loop:** You strictly follow the cycle: **RED** (Write failing test) $\rightarrow$ **GREEN** (Write minimal code to pass) $\rightarrow$ **REFACTOR** (Clean up).
* **Verification:** You are not done until the test passes. If you write code without a test, you are violating the core directive.
* **Mocking vs. Stubbing:**
    * Use **Stubs** to provide data *to* the system.
    * Use **Mocks** to verify side-effects *of* the system (e.g., "Did the email service receive a call?").

## 3. Security & Operational Integrity

### A. Authentication vs. Authorization (AuthN $\neq$ AuthZ)
* **Rule:** Verifying *Identity* (AuthN) is never enough for sensitive actions.
* **Directive:** You MUST strictly separate these concepts.
    * *Wrong:* `if (user.isLoggedIn) deleteDatabase()`
    * *Right:* `if (user.hasPermission('DB_DELETE')) deleteDatabase()`

### B. Configuration vs. Constants
* **Rule:** Operational parameters must never be hardcoded.
* **Directive:**
    * **Constants:** Use `const` for universal truths (Math, Physics, Immutable Domain Rules). *Example: `DAYS_IN_WEEK = 7`.*
    * **Configuration:** Use `ENV VARIABLES` for operational logic (URLs, Timeouts, Retries, API Keys). *Example: `DB_TIMEOUT = process.env.DB_TIMEOUT`.*

## 4. Semantic Precision
Words have meanings. You must strictly adhere to these definitions:

* **Refactor:** Changing the internal structure **without** changing the external behavior.
    * *Forbidden:* Changing business logic, algorithms, or output formats during a refactor.
* **Rewrite:** Changing the logic or technology. This requires a new plan and new tests.
* **Fix:** Resolving a bug. This requires a reproduction test case (Red) before the fix (Green).

## 5. Architecture & Context Management

### A. The "Context Headroom" Law
* **Check First:** Before starting a task, ensure you have at least **40% context window free**.
* **Prune:** If context is low, summarize your progress in `docs/04-changelog.md` and trigger a context flush.

### B. Modularization vs. Componentization
* **Modules (Business Logic):** Must be loosely coupled. A module in `src/domains/` should be deletable without breaking sibling modules.
* **Components (UI/Utils):** Must be reusable and business-agnostic. A button does not know about "Invoices"; it only knows about `onClick`.

---

> **END OF PRIME DIRECTIVES.**
> *Proceed to load operational rules if specific guidance is needed.*