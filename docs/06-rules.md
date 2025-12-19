# KHALA CODING STANDARDS (06-rules.md)

> **SYSTEM ROLE: SENIOR SOFTWARE ENGINEER**
> This file defines the **Implementation Standards**. It dictates how code is written, tested, and styled.

---

## 1. The TDD Protocol
We do not write "legacy code" (code without tests).

### A. The Cycle (Red-Green-Refactor)
1. **RED**: Write a test that fails (Assertion error only).
2. **GREEN**: Write the **simplest possible code** to pass.
3. **REFACTOR**: Clean up while keeping tests green.

### B. Mocking Rules
- **Stubs**: Use for inputs (avoid external dependencies).
- **Mocks**: Use only to verify side effects (e.g., "was email sent?").
- **Constraint**: Don't mock the logic being tested.

---

## 2. Semantic Precision
### A. Refactor vs. Fix
- **REFACTOR**: Identical I/O. No logic changes.
- **FIX**: Requires a reproduction test case (Red) before the fix.

### B. Commit Hygiene
- COMMITS must be atomic and descriptive.

---

## 3. Code Purity & Style
- **Pure Functions**: Prefer deterministic outputs over stateful classes.
- **File Limit**: No file should exceed **300 lines**. If it does, split responsibility.
- **Naming**: 
    - No cryptic abbreviations (`ctx` $\rightarrow$ `context`).
    - Booleans must be questions (`isValid`).
- **Magic Numbers**: **FORBIDDEN**. Use constants or enums.

---

## 4. Configuration vs. Constants
- **Constants**: Domain truths (hard rules).
- **Configuration**: Environment variables (`.env`). **NEVER** hardcode secrets or hostnames.

---

## 5. Error Handling
- **No Silent Failures**: Never swallow exceptions.
- **Protocol**: Catch $\rightarrow$ (Handle | Report | Rethrow).
- **Logging**: Use contextual structured logs, never raw `print`.
