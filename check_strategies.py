import os
import ast

def check_file_content(filepath, search_terms):
    if not os.path.exists(filepath):
        return []

    found = []
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            for term in search_terms:
                if term in content:
                    found.append(term)
    except Exception as e:
        pass
    return found

strategies = {
    "11_consolidation": {"file": "khala/application/services/memory_lifecycle.py", "terms": ["consolidate", "consolidation"]},
    "12_deduplication": {"file": "khala/application/services/memory_lifecycle.py", "terms": ["deduplicate", "content_hash"]},
    "15_ner": {"file": "khala/application/services/entity_extraction.py", "terms": ["extract_entities", "EntityExtractionService"]},
    "23_llm_cascading": {"file": "khala/infrastructure/gemini/client.py", "terms": ["generate_fast", "generate_smart", "Cascading"]},
    "25_mot": {"file": "khala/infrastructure/gemini/client.py", "terms": ["generate_mixture_of_thought"]},
    "49_multimodal": {"file": "khala/application/services/multimodal_service.py", "terms": ["process_image", "MultimodalService"]},
    "57_cost_tracker": {"file": "khala/infrastructure/gemini/cost_tracker.py", "terms": ["CostTracker", "track_cost"]},
    "100_query_expansion": {"file": "khala/application/services/query_expansion_service.py", "terms": ["QueryExpansionService", "expand_query"]},
    "118_episodic": {"file": "khala/application/services/episode_service.py", "terms": ["EpisodeService", "create_episode"]},
    "160_prompt_wizard": {"file": "khala/application/services/prompt_optimization.py", "terms": ["PromptOptimizationService", "optimize_prompt"]},
    "161_arm": {"file": "khala/application/services/reasoning_discovery.py", "terms": ["ReasoningDiscoveryService"]},
    "162_lgkgr": {"file": "khala/application/services/graph_reasoning.py", "terms": ["KnowledgeGraphReasoningService"]},
    "163_graphtoken": {"file": "khala/application/services/graph_token_service.py", "terms": ["GraphTokenService"]},
    "164_latent_mas": {"file": "khala/infrastructure/persistence/latent_repository.py", "terms": ["LatentRepository"]},
    "165_fulora": {"file": "khala/application/coordination/hierarchical_team.py", "terms": ["HierarchicalTeamService"]},
    "5_live": {"file": "khala/application/coordination/live_protocol.py", "terms": ["LiveProtocolService"]},
    "121_graph_rerank": {"file": "khala/application/services/hybrid_search_service.py", "terms": ["graph_rerank", "rerank"]},
    "35_skill_lib": {"file": "khala/infrastructure/persistence/skill_repository.py", "terms": ["SkillRepository"]},
    "46_sops": {"file": "khala/domain/sop", "terms": []}, # Directory check
    "51_ast": {"file": "khala/domain/code_analysis/parsers/python_parser.py", "terms": ["ast.parse"]},
    "13_background_jobs": {"file": "khala/infrastructure/background/scheduler.py", "terms": ["BackgroundScheduler"]},
    "26_verification": {"file": "khala/application/services/memory_lifecycle.py", "terms": ["verify", "verification"]},
}

print("Checking strategies...")
confirmed = []

for key, data in strategies.items():
    if data["file"].endswith("sop"): # Special directory check
        if os.path.exists(data["file"]):
            confirmed.append(key)
    else:
        found = check_file_content(data["file"], data["terms"])
        if found:
            confirmed.append(key)

print(f"Confirmed Logic: {len(confirmed)}")
print(confirmed)
