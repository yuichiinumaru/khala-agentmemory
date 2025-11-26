# Task Specification: Entity Extraction (NER) Service

## Overview
Implement comprehensive Named Entity Recognition (NER) service using Gemini API for intelligent entity extraction from memories with confidence scoring and relationship detection.

## Requirements

### 1. Core Components
- Create `khala/application/services/entity_extraction.py` with EntityExtractionService class
- Implement async entity extraction using Gemini 2.5 Pro
- Support multiple entity types: PERSON, ORGANIZATION, TOOL, CONCEPT, PLACE, EVENT, DATE, NUMBER
- Confidence scoring for each extracted entity (0.0-1.0)
- Relationship detection between entities within the same memory
- Batch processing capability for efficiency

### 2. Entity Types and Structure
```python
@dataclass
class ExtractedEntity:
    text: str                    # Original text span
    entity_type: EntityType       # Type of entity
    confidence: float            # Confidence score 0.0-1.0
    start_pos: int              # Start position in text
    end_pos: int                # End position in text
    metadata: Dict[str, Any]    # Additional entity data
    relationships: List[str]   # Related entity IDs
    extraction_method: str     # Method used: "gemini_llm"

@dataclass  
class EntityRelationship:
    source_entity_id: str
    target_entity_id: str
    relationship_type: str      # "works_at", "part_of", "related_to", etc.
    confidence: float
    context_snippet: str       # Text showing relationship
```

### 3. Technical Requirements

#### Gemini Integration
- Use prompt engineering optimized for entity extraction
- Implement few-shot examples in prompts for better accuracy
- Use structured output format (JSON) for consistent parsing
- Implement retry logic with exponential backoff
- Cache similar extractions for performance optimization

#### Processing Pipeline
```
Input Text → Gemini API → Structured Output → Entity Parsing → Confidence Scoring → Relationship Detection → Storage
```

#### Batch Processing
- Support batch processing of multiple memories
- Parallel processing with configurable concurrency (default: 4)
- Progress tracking and error handling for batch operations
- Memory-efficient processing for large texts

### 4. Quality Assurance

#### Accuracy Requirements
- Target accuracy: >85% for common entity types (PERSON, ORGANIZATION, PLACE)
- Confidence scoring calibration - actual accuracy should correlate with scores
- Minimal false positives in domain-specific entities (TOOL, CONCEPT)

#### Error Handling
- API rate limit handling with exponential backoff
- Input validation and sanitization
- Graceful degradation when Gemini is unavailable
- Comprehensive logging for debugging

### 5. Integration Points

#### With KHALA Memory System
- Store extracted entities in `khala/domain/memory/entities.py` Memory entity
- Update memory relationships in `Relationship` entities
- Trigger entity enrichment processes
- Support entity-based memory search and retrieval

#### With Database
- Store entities in SurrealDB `entity` table
- Store relationships in `relationship` table
- Query entity mentions efficiently
- Support entity-based indexing

### 6. Performance Requirements

#### Benchmarks
- Single memory extraction: <2 seconds
- Batch processing (10 memories): <3 seconds  
- Parallel throughput: >50 memories/minute with 4 workers
- Memory usage: <200MB for typical workloads

#### Optimization
- Implement intelligent caching for repeated extractions
- Use batch API calls when possible
- Optimize prompts for minimal token usage
- Implement result caching with TTL

### 7. File Structure
```
khala/application/services/
├── __init__.py
├── entity_extraction.py     # Main service implementation
├── entity_types.py         # Entity type definitions
├── prompts.py             # Gemini prompts for extraction
└── cache.py              # Caching utilities

khala/tests/services/
├── test_entity_extraction.py  # Comprehensive tests
├── test_integration.py       # Integration tests
└── fixtures/                # Test data
```

### 8. Testing Requirements

#### Unit Tests
- Test all entity types extraction
- Test confidence scoring accuracy
- Test relationship detection
- Test error handling and edge cases
- Test batch processing functionality

#### Integration Tests
- Test integration with Gemini API
- Test database storage and retrieval
- Test KHALA memory entity updates
- Test cache functionality

#### Performance Tests
- Benchmark extraction speed
- Test scalability with large datasets
- Test memory usage with batch processing
- Test cache performance

### 9. Documentation Requirements

#### API Documentation
- Complete docstrings for all public methods
- Type hints using Python typing
- Usage examples and best practices
- Error handling documentation

#### Configuration Documentation
- Environment variables and configuration options
- Performance tuning guidelines
- Cache configuration documentation

### 10. Dependencies

#### Required
- Google Generative AI library (google-generativeai)
- Existing KHALA domain classes and entities
- SurrealDB client for storage

#### Optional
- Redis for caching (falls back to in-memory if not available)
- spaCy or similar NLP library for fallback processing
- pytest for testing

## Success Criteria

1. All entity types supported with >85% accuracy
2. Confidence scoring properly calibrated
3. Batch processing performance benchmarks met
4. Full integration with KHALA memory system
5. Comprehensive test coverage (>90%)
6. Production-ready error handling and logging
7. Performance optimization with caching

## Expected Deliverables

1. Complete service implementation with all entity types
2. Comprehensive test suite with >90% coverage
3. Integration tests with KHALA memory system
4. Performance benchmarks and optimization
5. Complete documentation and usage examples
6. Configuration management and deployment guides

## Implementation Guidelines

Follow existing KHALA patterns:
- Use Domain-Driven Design principles
- Implement comprehensive error handling
- Use structured logging throughout
- Follow PEP 8 and existing code style
- Write type hints and docstrings
- Include unit tests for all functionality
