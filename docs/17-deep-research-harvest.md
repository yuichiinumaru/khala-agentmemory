# Deep Research Harvest: Architecture & Strategy

**Source**: Analysis of Top-Tier Research Agents (Salesforce, Alibaba, LangChain, dzhng)
**Date**: December 2025
**Status**: Analysis & Integration Plan

---

## 🧠 Executive Summary
The "Deep Research" domain has converged on a standard architectural pattern: **Iterative Expansion with Reflection**. The best systems do not just "search once"; they recursively explore a knowledge tree, guided by a planner that identifies gaps.

Khala's `ResearchTeam` is a good start (Researcher-Analyst-Critic), but it lacks the **recursive depth** and **dynamic planning** found in SOTA systems.

---

## 1. The "Standard Model" of Deep Research

### A. The Planner / Master Agent (Salesforce, LangChain)
*   **Role**: Decomposes the high-level user query into a set of specific sub-questions (SERP queries).
*   **Mechanism**: `Query -> Decompose -> List[SubQueries]`.
*   **Khala Gap**: Our `Researcher` just searches for the raw objective text. It needs a planning step.

### B. The Breadth/Depth Algorithm (dzhng/deep-research)
*   **Concept**:
    *   **Breadth**: How many parallel queries to generate per step.
    *   **Depth**: How many layers of recursion (Question -> Answer -> Follow-up Question).
*   **Khala Gap**: We have a single pass. We need a `max_depth` parameter.

### C. The Reflection Loop (Alibaba, LangChain)
*   **Concept**: After summarizing results, the agent asks: "What is missing? What contradicts?"
*   **Action**: Generates *new* queries specifically to fill those gaps.
*   **Khala Gap**: Our `Critic` reviews the final insight, but doesn't trigger *new* searches during the process.

---

## 🚀 Integration Strategy: "The Khala Deep Drill"

We will upgrade `ResearchTeam` to implementing a **Depth-First Search (DFS) with Breadth Control**, orchestrated by a new `PlannerAgent`.

### New Components

1.  **PlannerAgent**:
    *   Input: User Objective.
    *   Output: `ResearchPlan` (List of initial questions).
    *   Capability: Can update the plan based on new findings.

2.  **Recursive Research Loop**:
    *   Instead of `execute_mission` doing a linear 1-2-3-4, it becomes:
        ```python
        plan = planner.create_plan(objective)
        knowledge_bank = []

        for step in range(max_depth):
            for question in plan.current_questions:
                docs = researcher.gather(question)
                insights = analyst.synthesize(docs)
                knowledge_bank.extend(insights)

            # Reflection Point
            gaps = critic.identify_gaps(knowledge_bank, objective)
            if not gaps: break

            plan = planner.update_plan(gaps)
        ```

3.  **Source Tracking**:
    *   Every finding must be linked to a `Memory` ID (the source document).

---

## 🛠️ Implementation Plan

### Step 1: Refactor `ResearchTeam`
*   Add `PlannerAgent`.
*   Implement `run_recursive_research(depth, breadth)`.

### Step 2: Upgrade `StudyService`
*   Expose `depth` and `breadth` parameters in `conduct_deep_study`.

### Step 3: Persistence
*   Store the *Plan* itself as a memory, updated in real-time, so we can visualize the research progress (like Salesforce's UI).

---

## 📊 Expected Improvements
*   **Coverage**: Will find obscure details by drilling down.
*   **Self-Correction**: Will notice missing info and actively look for it.
*   **Structure**: The final report will be much more comprehensive.
