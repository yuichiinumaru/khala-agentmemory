#!/usr/bin/env python3

import sys
sys.path.insert(0, '/home/suportesaude/YUICHI/06-NEXUS/khala')

from khala.domain.search.value_objects import SearchIntent

# Test intent classification
test_queries = [
    "What is Python?",
    "Who is the president?", 
    "When was JavaScript created?",
    "Where is Paris located?",
    "Tell me about machine learning"
]

print("Testing intent classification:")
for query in test_queries:
    intent = SearchIntent.classify_text(query)
    print(f"'{query}' -> {intent}")
    
    # Debug: show what patterns are being matched
    query_lower = query.lower()
    factual_patterns = ["what is", "who is", "when did", "where is", "tell me about"]
    for pattern in factual_patterns:
        if pattern in query_lower:
            print(f"  Matched pattern: '{pattern}'")
            break
    else:
        print("  No factual pattern matched")
