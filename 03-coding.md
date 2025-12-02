Here is the draft for **`03-coding.md`**.

This file acts as the **Senior Code Reviewer**. It focuses on the specific lines of code, variable naming, testing patterns, and implementation details. It ensures the code is not just "working," but clean, maintainable, and correct.

-----

# 03-coding.md

> **SYSTEM ROLE: SENIOR SOFTWARE ENGINEER**
> This file defines the **Implementation Standards**. It dictates how code is written, tested, and styled.
> **Consult this file when writing functions, classes, tests, or fixing bugs.**

-----

## 1\. The TDD Protocol (Implementation Level)

We do not write "legacy code" (code without tests).

### A. The Cycle

1.  **RED:** Write a test that fails.
      * *Constraint:* The test must fail for the *right reason* (assertion error, not syntax error).
2.  **GREEN:** Write the **simplest possible code** to pass the test.
      * *Constraint:* Do not implement future features here. Just pass the test.
3.  **REFACTOR:** Clean up the code.
      * *Constraint:* Tests must stay Green.

### B. Mocking vs. Stubbing

Distinguish between "Input Replacement" and "Output Verification".

  * **Stubs (Inputs):** Use stubs to provide data *to* your function to avoid external dependencies (e.g., "When `getWeather()` is called, return `{ temp: 20 }`").
  * **Mocks (Side Effects):** Use mocks to verify that an action happened (e.g., "Verify `emailService.send()` was called exactly once with `admin@example.com`").
  * **Rule:** **Don't mock everything.** If you mock the logic you are testing, the test is worthless.

-----

## 2\. Semantic Precision

Your commit intent determines your allowed actions.

### A. Refactor vs. Rewrite

  * **REFACTOR:**
      * **Input/Output:** MUST remain identical.
      * **Allowed:** Renaming variables, extracting functions, simplifying loops.
      * **FORBIDDEN:** Changing business logic, fixing bugs (do that in a separate commit), or upgrading libraries.
  * **FIX:**
      * **Requirement:** You MUST create a reproduction test case (Red) that proves the bug exists *before* fixing it.
      * **Anti-Pattern:** Blindly applying fixes without a test case is strictly forbidden.

-----

## 3\. Code Style & purity

### A. Pure Functions

  * **Preference:** Prefer "Pure Functions" (deterministic output based solely on inputs) over stateful classes.
  * **Reasoning:** Pure functions are easier to test and parallelize.
  * **Example:**
      * *Bad:* `function calculateTotal() { return this.price * globalTax; }`
      * *Good:* `function calculateTotal(price, taxRate) { return price * taxRate; }`

### B. File Constraints

  * **Limit:** No file should exceed **300 lines** of code.
  * **Action:** If a file grows beyond 300 lines, it is a strong signal that it has multiple responsibilities. **Split it.**

### C. Naming Conventions

  * **No Cryptic Abbreviations:** `usr` $\rightarrow$ `user`, `ctx` $\rightarrow$ `context`.
  * **Booleans:** Must answer a question. `isValid`, `hasAccess`, `isPending`.
  * **Magic Numbers:** **FORBIDDEN.**
      * *Bad:* `if (status === 3)`
      * *Good:* `const STATUS_COMPLETED = 3; if (status === STATUS_COMPLETED)`

-----

## 4\. Configuration vs. Constants

We strictly separate "World Truths" from "Operational Settings".

### A. Constants (The "Math" of the Domain)

Values that are universally true for the business logic.

  * **Implementation:** Use `const` or `enums` inside the code.
  * *Example:* `const MAX_RETRY_LIMIT = 3;` (If this is a hard business rule).

### B. Configuration (The Environment)

Values that change depending on where the code runs (Local, Staging, Prod).

  * **Implementation:** MUST come from Environment Variables (`process.env`).
  * **Forbidden:** Hardcoding API URLs, Secrets, or Database paths.
  * *Example:* `const API_URL = process.env.API_URL;`

-----

## 5\. Error Handling

Do not fail silently. Do not "swallow" errors.

  * **Catching:** If you `catch` an error, you must either:
    1.  **Handle it:** (e.g., use a fallback value).
    2.  **Report it:** (e.g., log to monitoring).
    3.  **Rethrow it:** (wrap it in a contextual error).
  * **Anti-Pattern:**
    ```javascript
    try {
      dangerousOp();
    } catch (e) {
      // TODO: handle this
      console.log("oops"); // STRICTLY FORBIDDEN
    }
    ```

-----

> **END OF CODING STANDARDS.**
> *Return to `00-prime-directives.md` for governance queries.*