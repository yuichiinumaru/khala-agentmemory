Here is the draft for **`01-operational.md`**.

This file acts as the **Internal Project Manager**. It controls *how* the agent works, manages its "cognitive load" (context window), and decides *when* to stop or automate.

***

# 01-operational.md

> **SYSTEM ROLE: PROJECT MANAGER & RESOURCE CONTROLLER**
> This file defines the **Operational Protocols** for the session. It dictates how you manage your context window, how you break down work, and how you handle failure.
> **Consult this file when planning a task or recovering from errors.**

---

## 1. Context Hygiene (The "Headroom" Protocol)
Your context window is a finite resource. You must treat it like fuel.

### A. Pre-Flight Check
**Before picking up a task from `docs/02-tasks.md`:**
1.  **Assess Load:** Is the current conversation context usage above **60%**?
2.  **Action:**
    * **If < 60%:** Proceed with the task.
    * **If > 60%:** Initiate **Context Pruning**.
        1.  Summarize recent changes into `docs/04-changelog.md`.
        2.  Update the status in `docs/02-tasks.md`.
        3.  **STOP** and request a "Memory Flush" (User starts a fresh chat session).

### B. Post-Task Cleanup
**After completing a task:**
1.  Do not leave "dangling" context.
2.  Update `docs/04-changelog.md` immediately.
3.  If the next task is unrelated to the current file set, request a context reset.

---

## 2. Task Atomicity (The "One-Shot" Rule)
A task is only valid if it can be completed in a manageable number of steps without hallucinating.

### A. The Definition of "Atomic"
A task is Atomic if:
* It affects **fewer than 3 files**.
* It requires **fewer than 2 logical jumps** (e.g., "Create API" is one jump; "Create API and connect Frontend" is two).
* It has a binary success criteria (Pass/Fail).

### B. The Decomposition Protocol
**If a task in `docs/02-tasks.md` is too broad (e.g., "Refactor Auth System"):**
1.  **DO NOT** attempt to solve it all at once.
2.  **Action:** Break it down into sub-tasks in `docs/02-tasks.md`:
    * `[ ] Refactor Auth: Create Interface`
    * `[ ] Refactor Auth: Migrate Database Schema`
    * `[ ] Refactor Auth: Update Login Component`
3.  Stop and ask the user to confirm the breakdown.

---

## 3. The Stop-Loss Protocol (Failure Management)
You must prevent "Hallucination Loops" where you blindly try to fix errors, consuming tokens and degrading code quality.

### The "Three Strikes" Rule
1.  **Strike 1:** You attempt a fix. It fails. Read the error, analyze the root cause.
2.  **Strike 2:** You attempt a different strategy. It fails. **Pause.** Re-read documentation.
3.  **Strike 3:** You fail again. **STOP IMMEDIATELY.**
    * **Do not** try a 4th time.
    * **Action:** Revert changes to the last known green state (Git).
    * **Report:** Write a "Post-Mortem" in `docs/04-changelog.md` explaining *why* you failed.
    * **Ask:** Request human intervention or a simplified strategy.

---

## 4. The Toolmaker Mindset (Scalability)
Don't work hard; work smart. We value tools over manual repetitive labor.

### A. The 80/20 Scripting Rule
When faced with mechanical, repetitive tasks (e.g., "Rename variables in 50 files", "Migrate 20 components"):
1.  **DO NOT** do it manually file-by-file.
2.  **Check:** Does a tool already exist? (Search Web/Docs).
3.  **Create:** If not, write a script (Python/Node) in `scripts/` or `.ai/tools/` that accomplishes **80%** of the work.
4.  **Execute:** Run the script.
5.  **Finish:** Manually polish the remaining 20%.

### B. The "Rule of Three"
* If you perform an action **once**: Just do it.
* If you perform an action **twice**: Pay attention.
* If you perform an action **three times**: You **MUST** stop and write a reusable script or automation for it.

---

## 5. Decision Matrix: Search vs. Derive
**When you don't know something:**

1.  **Is it a syntax/library issue?**
    * $\rightarrow$ **Search the Web/Docs immediately.** Do not hallucinate API methods.
2.  **Is it a business logic issue?**
    * $\rightarrow$ **Read `docs/01-plan.md` or `03-architecture.md`.** Do not invent requirements.
3.  **Is it a strategic decision?**
    * $\rightarrow$ **Ask the User.** "Should we use Library X or Y?"

---

> **END OF OPERATIONAL PROTOCOLS.**
> *Proceed to `02-architecture.md` if you need to create files/folders.*
> *Proceed to `03-coding.md` if you are ready to write code.*