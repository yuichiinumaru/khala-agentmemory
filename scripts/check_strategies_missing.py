import os
import re

# 1. Define the known implemented strategy IDs based on previous context
implemented_ids = [
    # Core (1-22) - Mostly implemented in Schema/Core Services
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 21, 22,
    # Advanced (23-57)
    23, 24, 25, 26, 27, 28, 29, 35, 39, 41, 44, 46, 49, 51, 56, 57,
    # SurrealDB Opt (58-77 Graph/Doc) - Many are schema features
    58, 60, 61, 62, 63, 67, 71, 77, 78, 87, 93, 100, 103,
    # Experimental (116-159)
    118, 121, 135, 136, 160, 161, 162, 163, 164, 165, 166
]

# 2. Define the full list map (simplified for checking)
all_strategies = {
    # Populated from the read_file output manually to ensure accuracy in the next step
    # I will rely on the diff logic:
    # If I know it's implemented -> skip
    # If I don't see evidence -> add to missing
}

# 3. Check specific files for evidence of "maybe" implemented ones
evidence_checks = {
    "30_intent": ("khala/application/services/debug_intent.py", "Intent"),
    "33_topic": ("khala/application/services/topic_detection_service.py", "Topic"),
    "34_pattern": ("khala/application/services/pattern_recognition_service.py", "Pattern"),
    "17_trigger": ("khala/application/services/memory_lifecycle.py", "trigger"),
    "40_execution_eval": ("khala/domain/code_analysis", "execution"),
    "132_privacy": ("khala/domain/audit", "redact"),
    "159_self_healing": ("khala/infrastructure/vector", "heal"),
}

found_extras = []
for key, (path, term) in evidence_checks.items():
    if os.path.exists(path):
         found_extras.append(key)

print(f"Found extras: {found_extras}")
