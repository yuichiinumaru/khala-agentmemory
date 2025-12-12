# The Consolidated Scavenger Manifest

## Part 1: The Source Matrix

| Repo Name | Core Strength | Verdict (Keep/Discard) |
| :--- | :--- | :--- |
| `Acontext` | Context Data Platform SDK | **KEEP** (Python SDK only) |
| `memobase` | Memory Client & Patching | **KEEP** (Python Client) |
| `nano-manus` | Agent Loop & MCP Integration | **KEEP** (Core Logic) |
| `drive-flow` | Event-Driven Workflow Engine | **KEEP** (Core Engine) |
| `prompt-string` | Object-Oriented Prompting | **KEEP** (Full Lib) |
| `PersonaMem` | Evaluation & Benchmarking | **KEEP** (Scripts & Data) |
| `aichemy` | SQLAlchemy Hooks | **DISCARD** (Incompatible Stack) |
| `memobase-playground` | UI/Frontend | **DISCARD** (Out of Scope) |
| `memobase-inspector` | UI/Frontend | **DISCARD** (Out of Scope) |
| `memobase-helm` | DevOps/Charts | **DISCARD** (Out of Scope) |
| `Acontext-Examples` | Usage Examples | **DISCARD** (Redundant) |
| `memory-benchmark` | Basic Benchmarks | **DISCARD** (Superseded by PersonaMem) |
| `memobase-data-fixtures`| Data Fixtures | **DISCARD** (Empty/Irrelevant) |
| `memobase-issues` | Issue Tracking | **DISCARD** (Empty/Irrelevant) |

## Part 2: The Champions List (Feature Extraction)

### Feature Category: Agent Orchestration & Planning
* **Winner:** `nano-manus`
* **Why it won:** Implements a clean `Planner` loop with step parsing (`parse_step`) and a robust worker system (`mcp_agent`, `code_agent`) that integrates directly with Model Context Protocol (MCP).
* **Integration Strategy:** Adapt the `Planner` class and `worker` module to enhance Khala's `PlanningService` and tool execution capabilities.

### Feature Category: Event-Driven Architecture
* **Winner:** `drive-flow`
* **Why it won:** Provides a sophisticated `EventEngineCls` that handles event dependency graphs, grouping (`listen_group`), and async execution flows.
* **Integration Strategy:** Evaluate `drive_flow` for Khala's internal signaling system, potentially replacing or augmenting the current simple event handlers.

### Feature Category: Prompt Engineering
* **Winner:** `prompt-string`
* **Why it won:** Treats prompts as first-class objects (`PromptString`, `PromptChain`) with built-in role management and token counting.
* **Integration Strategy:** Adopt `PromptString` utility to refactor raw string prompts in Khala, improving maintainability and type safety.

### Feature Category: Memory Client SDK
* **Winner:** `memobase` & `Acontext` (Hybrid)
* **Why it won:** `memobase` has excellent `blob` and `entry` management. `Acontext` features a well-structured async client design.
* **Integration Strategy:** Reference `memobase` for blob storage patterns and `Acontext` for SDK structure when refining Khala's client-facing APIs.

## Part 3: The Action Plan (`docs/02-tasks.md`)

* `[ ]` **Ref: `nano-manus`** - Extract `Planner` and `worker` logic to upgrade Khala's planning capabilities.
* `[ ]` **Ref: `drive-flow`** - Analyze `EventEngineCls` for potential adoption in `Khala`'s event system.
* `[ ]` **Ref: `prompt-string`** - Integrate `PromptString` utility into `khala/domain/prompt`.
* `[ ]` **Ref: `memobase`** - Review `patch/openai.py` for potential interception strategies in Khala.
* `[ ]` **Cleanup:** Remove discarded repositories from `references/` to maintain hygiene.
