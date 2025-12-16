import json
import os
import argparse

RELEVANCE_KEYWORDS = {
    "memory": 2, "long-term": 2, "hierarchical": 2, "agent": 2, "planning": 2,
    "security": 2, "injection": 2, "retrieval": 2, "graph": 2, "vector": 2,
    "embedding": 2, "multimodal": 2, "vlm": 2, "reasoning": 2, "reflection": 2,
    "consolidation": 2, "lifecycle": 2, "gate": 2, "intent": 2, "adversarial": 2,
    "benchmark": 1, "evaluation": 1, "framework": 1, "architecture": 1
}

def calculate_relevance(text):
    text = text.lower()
    score = 0
    found_keywords = []
    for kw, val in RELEVANCE_KEYWORDS.items():
        if kw in text:
            score += val
            found_keywords.append(kw)
    return score, found_keywords

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--consolidate", action="store_true", help="Generate consolidated report only")
    args = parser.parse_args()

    json_path = "docs/arcticles/harvested.json"
    if not os.path.exists(json_path):
        print("Harvested JSON not found.")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    # Consolidate logic (runs separately or if specified)
    if args.consolidate:
        consolidated_report = "# Consolidated Harvest Report\n\n"
        consolidated_report += "This report consolidates ideas from the harvested arXiv articles, focusing on high-relevance papers for Khala.\n\n"
        high_value_ideas = []
        for item in data:
            relevance_score, keywords = calculate_relevance(item["title"] + " " + item["summary"])
            if relevance_score >= 4:
                item['keywords'] = keywords
                high_value_ideas.append(item)

        consolidated_report += "## High Value Candidates for Integration\n\n"
        for item in high_value_ideas:
            consolidated_report += f"### [{item['title']}]({item['link']})\n"
            consolidated_report += f"- **Summary**: {item['summary'][:300]}...\n"
            consolidated_report += f"- **Relevance**: High overlap with Khala goals ({', '.join(item['keywords'])}).\n\n"

        with open("docs/17-deep-research-harvest-consolidated.md", "w") as f:
            f.write(consolidated_report)
        print("Generated consolidated report.")
        return

    # Batch processing for individual files
    batch_data = data[args.offset : args.offset + args.limit]
    print(f"Processing batch {args.offset} to {args.offset + len(batch_data)}...")

    for item in batch_data:
        relevance_score, keywords = calculate_relevance(item["title"] + " " + item["summary"])

        # Determine Offering
        offering = "## Analysis for Khala\n"
        if relevance_score >= 4:
            offering += f"**Status:** Highly Relevant\n"
            offering += f"**Keywords:** {', '.join(keywords)}\n\n"
            offering += "This paper presents concepts directly applicable to Khala's core architecture (Memory, Reasoning, Security). "
            offering += "We should investigate integrating its findings into the Domain or Infrastructure layers."
        elif relevance_score > 0:
            offering += f"**Status:** Potentially Useful\n"
            offering += f"**Keywords:** {', '.join(keywords)}\n\n"
            offering += "This paper touches on relevant topics and may offer auxiliary insights or optimization strategies."
        else:
            offering += "**Status:** Low Direct Relevance\n"
            offering += "This paper appears to focus on topics outside the immediate scope of Khala's current roadmap, but is preserved for completeness."

        content = f"# {item['title']}\n"
        content += f"**Link**: {item['link']}\n\n"
        content += "## Summary\n"
        content += f"{item['summary']}\n\n"
        content += "## Offering to Project\n"
        content += f"{offering}\n"

        filename = f"docs/arcticles/{item['id']}.md"
        with open(filename, "w") as f:
            f.write(content)

    print(f"Generated {len(batch_data)} reports.")

if __name__ == "__main__":
    main()
