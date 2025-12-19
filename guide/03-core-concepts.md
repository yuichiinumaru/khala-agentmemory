# The Glossary: Core Concepts

To speak Khala, you must understand its vocabulary.

## 1. The Atoms of Memory

### Memory (`vivi:memory`)
The fundamental unit. A single block of information.
- **Attributes**: `content`, `embedding`, `timestamps`, `importance`.
- **Analogy**: A neuron firing.

### Entity (`vivi:entity`)
A specific noun extracted from a memory.
- **Types**: `PERSON`, `PLACE`, `OBJECT`, `CONCEPT`.
- **Analogy**: A concept stored in the brain.

### Episode (`vivi:episode`)
A temporal sequence of memories. Usually corresponds to a single conversation or task.
- **Analogy**: A scene in a movie.

## 2. The Forces of Nature

### Consolidtion ("Dreaming")
The process where Khala takes fragmented Tier 1/2 memories and synthesizes them into Tier 3 wisdom.
- **Service**: `DreamService`.
- **When**: During agent idle time.
- **Output**: New "Summary Memories" that represent patterns.

### Entropy ("Decay")
All memories fade over time unless reinforced.
- **Formula**: `Score = Importance * (1 / (1 + TimeDecay * Elapsed))`.
- **Effect**: Low score memories are archived or forgotten.
- **Counter**: Inspecting or using a memory "refreshes" it (Spaced Repetition).

### Deterministic Flows
Complex actions that must happen efficiently and reliably.
- **Example**: `IngestFlow` (Extract -> Embed -> Store).
- **Service**: `FlowOrchestrator`.
- **Note**: Flows are robust; if they fail, they self-correct or rollback.

## 3. Cognitive Protocols

### Hypothesis Testing
Khala doesn't just store facts; it generates hypotheses.
- *"User ordered coffee at 8AM everyday. Hypothesis: User is a morning person."*
- Future observations verify or falsify this.

### Reflection
The agent queries its own memory to answer "Why did I do that?" or "What do I know about X?".
