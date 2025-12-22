# 01-PLAN.md
# KHALA v2.0: Complete Memory System Implementation Plan

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)  
**Version**: 2.0  
**Framework**: Agno + SurrealDB  
**Date**: November 2025  
**Status**: Planning Complete

---

## EXECUTIVE SUMMARY

### Project Vision

Build a **production-ready, template-based Agno agent** that serves as the foundation for all future agent development. This agent will integrate **57 memory optimization strategies** (22 core + 35 advanced) into a single, cohesive system that can be cloned and customized for specific use cases.

### Core Objective

Create one **functional reference agent** with:
- Complete implementation of all 57 strategies
- Production-grade code quality
- Comprehensive documentation
- Reusable as a template for future agents

### Key Deliverables

1. **Single Template Agent**: Fully functional Agno agent with integrated memory system
2. **Documentation Suite**: Complete technical and operational documentation
3. **Test Suite**: Comprehensive testing framework
4. **Deployment Kit**: Production deployment scripts and configuration

---

## PROJECT SCOPE

### In Scope

#### Core Implementation (22 Strategies)
1. Vector Storage with HNSW indexing
2. Graph Relationships (entities + edges)
3. Document Model (flexible JSON)
4. RBAC Multi-tenancy
5. LIVE Real-time Subscriptions
6. Hybrid Search (Vector + BM25 + Metadata)
7. L1/L2/L3 Cache System
8. Context Assembly (token management)
9. 3-Tier Memory Hierarchy
10. Auto-Promotion Logic
11. Consolidation System
12. Deduplication (hash + semantic)
13. Background Job Processing
14. Temporal Analysis
15. Entity Extraction (NER)
16. Metadata & Tags System
17. Natural Memory Triggers
18. MCP Interface
19. Multi-Agent Coordination
20. Monitoring & Health Checks
21. Decay Scoring
22. Agent-to-Agent Communication

#### Advanced Implementation (35 Strategies)

**Cost Optimization (3)**
23. LLM Cascading (fast/medium/smart routing)
24. Consistency Signals (confidence-based routing)
25. Mixture of Thought (parallel paths)

**Quality Assurance (3)**
26. Self-Verification Loop (6-check gate)
27. Multi-Agent Debate (consensus voting)
28. Information Traceability (provenance tracking)

**Search Enhancement (6)**
29. BM25 Full-Text Search
30. Query Intent Classification
31. Significance Scoring
32. Multi-Perspective Question Asking
33. Topic Change Detection
34. Cross-Session Pattern Recognition

**Memory Optimization (4)**
35. Skill Library System
36. Instruction Registry
37. Emotion-Driven Memory
38. Advanced Multi-Index Strategy

**Production Features (10)**
39. Audit Logging System
40. Execution-Based Evaluation
41. Bi-temporal Graph Edges
42. Hyperedges (N-ary relationships)
43. Relationship Inheritance
44. Distributed Consolidation
45. Modular Component Architecture
46. Standard Operating Procedures
47. Von Neumann Pattern (control/data separation)
48. GPU Acceleration

**Advanced Features (9)**
49. Multimodal Support (image/table/code)
50. Cross-Modal Retrieval
51. AST Code Representation
52. Multi-Step Planning with Verification
53. Hierarchical Task Decomposition
54. Hypothesis Testing Framework
55. Context-Aware Tool Selection
56. Graph Visualization Dashboard
57. LLM Cost Dashboard

### Out of Scope

- Multiple agent templates (only 1 reference agent)
- Custom UI/UX beyond admin dashboard
- Mobile applications
- Third-party integrations beyond MCP
- Custom LLM training
- Federated deployment (single-node only initially)

---

## TECHNICAL ARCHITECTURE

### Stack Selection

**Primary Stack** (Mandatory)
- **Agent Framework**: Agno (https://github.com/agno-agi/agno)
- **Database**: SurrealDB 2.0+ (https://surrealdb.com)
- **Embedding Model**: gemini-embedding-001 (768 dimensions)
- **LLM Primary**: gemini-3-pro-preview
- **LLM Fast**: gemini-1.5-flash
- **LLM Medium**: gpt-4o-mini (OpenAI)
- **Language**: Python 3.11+

**Supporting Infrastructure**
- **Cache L2**: Redis 7+ (optional but recommended)
- **GPU**: CUDA 12+ with ONNX Runtime (for acceleration)
- **Monitoring**: Prometheus + Grafana
- **Documentation**: Markdown + Sphinx
- **Testing**: pytest + pytest-asyncio
- **CI/CD**: GitHub Actions

### System Layers

```
┌──────────────────────────────────────────────────────────┐
│ Layer 1: APPLICATION (Agno Agent)                       │
│ - Template agent with all 57 strategies                  │
│ - User interaction & orchestration                       │
└──────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 2: INTELLIGENCE (Memory System)                   │
│ - Intent classification & routing                        │
│ - Multi-agent debate & consensus                         │
│ - Skill library & pattern extraction                     │
│ - Verification & quality gates                           │
└──────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 3: RETRIEVAL (Hybrid Search)                      │
│ - Vector search (HNSW)                                   │
│ - BM25 full-text search                                  │
│ - Metadata filtering                                     │
│ - Graph traversal                                        │
│ - Significance scoring                                   │
└──────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 4: STORAGE (SurrealDB)                            │
│ - Vector: HNSW indexes                                   │
│ - Graph: Entities + relationships                        │
│ - Document: Flexible JSON                                │
│ - Temporal: Bi-temporal edges                            │
│ - Multimodal: Images/tables/code                         │
└──────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│ Layer 5: OPTIMIZATION (Background)                      │
│ - Decay scoring                                          │
│ - Consolidation & merging                                │
│ - Deduplication                                          │
│ - Pattern extraction → Skill library                     │
│ - Distributed processing                                 │
└──────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION STRATEGY

### Development Approach

**Methodology**: Agile + DDD (Domain-Driven Design)

**Module Organization** (following DDD principles):
```
khala/
├── domain/                  # Business logic (pure)
│   ├── memory/             # Memory domain
│   ├── search/             # Search domain
│   ├── agent/              # Agent domain
│   └── consolidation/      # Consolidation domain
├── infrastructure/          # Technical implementations
│   ├── surrealdb/          # SurrealDB adapter
│   ├── gemini/             # Gemini API client
│   ├── cache/              # Redis cache
│   └── gpu/                # GPU acceleration
├── application/             # Application services
│   ├── services/           # Business services
│   ├── orchestration/      # Multi-agent orchestration
│   └── verification/       # Quality gates
└── interface/               # External interfaces
    ├── cli/                # CLI interface
    ├── mcp/                # MCP server
    └── api/                # REST API
```

### Implementation Phases

**Phase Structure**: Modular, not sequential (any module can be started independently)

#### Module 1: Foundation (Core 1-5)
- SurrealDB setup & schema
- Vector storage with HNSW
- Graph relationships
- Document model
- Multi-tenancy setup

**Dependencies**: None  
**Estimated Effort**: 40 hours  
**Success Criteria**: Database operational, basic CRUD working

#### Module 2: Search System (Core 6-8 + Advanced 29-30)
- Hybrid search implementation
- BM25 integration
- Cache layers (L1/L2/L3)
- Context assembly
- Intent classification

**Dependencies**: Module 1  
**Estimated Effort**: 48 hours  
**Success Criteria**: Search precision >85%, latency p95 <100ms

#### Module 3: Memory Lifecycle (Core 9-12)
- 3-tier hierarchy
- Auto-promotion logic
- Consolidation system
- Deduplication

**Dependencies**: Modules 1, 2  
**Estimated Effort**: 32 hours  
**Success Criteria**: Memory promotion working, dedup >90% accuracy

#### Module 4: Processing & Analysis (Core 13-17 + Advanced 35-36)
- Background jobs
- Temporal analysis
- Entity extraction
- Metadata & tags
- Natural triggers
- Skill library

**Dependencies**: Modules 1, 2, 3  
**Estimated Effort**: 56 hours  
**Success Criteria**: Entities extracted >85% accuracy, skills cataloged

#### Module 5: Integration & Coordination (Core 18-22)
- MCP interface
- Multi-agent coordination
- Monitoring & health
- Agent communication

**Dependencies**: Modules 1, 2, 3, 4  
**Estimated Effort**: 40 hours  
**Success Criteria**: Agents can coordinate, MCP tools working

#### Module 6: Cost Optimization (Advanced 23-25)
- LLM cascading
- Consistency signals
- Mixture of thought

**Dependencies**: All previous modules  
**Estimated Effort**: 32 hours  
**Success Criteria**: Cost reduction -60%, quality maintained

#### Module 7: Quality Assurance (Advanced 26-28)
- Self-verification loop
- Multi-agent debate
- Information traceability

**Dependencies**: Module 5  
**Estimated Effort**: 32 hours  
**Success Criteria**: Quality improvement +20%, verification >70% pass rate

#### Module 8: Advanced Search (Advanced 31-34)
- Significance scoring
- Multi-perspective questions
- Topic change detection
- Cross-session patterns

**Dependencies**: Module 2  
**Estimated Effort**: 24 hours  
**Success Criteria**: Relevance +15%, pattern discovery working

#### Module 9: Production Features (Advanced 39-48)
- Audit logging
- Execution testing
- Bi-temporal edges
- Hyperedges
- Distributed consolidation
- Modular architecture
- SOPs
- GPU acceleration

**Dependencies**: All previous modules  
**Estimated Effort**: 64 hours  
**Success Criteria**: Production-ready, audit trail complete, GPU 5x speedup

#### Module 10: Advanced Capabilities (Advanced 49-57)
- Multimodal support
- Cross-modal retrieval
- AST parsing
- Multi-step planning
- Hierarchical decomposition
- Hypothesis testing
- Tool selection
- Dashboards (graph viz + cost)

**Dependencies**: Module 9  
**Estimated Effort**: 72 hours  
**Success Criteria**: Multimodal working, dashboards deployed

---

## RESOURCES & DEPENDENCIES

### Team Requirements

**Minimum Viable Team**:
- 1 Senior Python Engineer (Agno + SurrealDB experience)
- 1 ML Engineer (for embeddings & GPU optimization)

**Optimal Team**:
- 1 Tech Lead / Architect
- 2 Senior Engineers
- 1 ML Engineer
- 1 DevOps Engineer
- 1 Technical Writer

### Infrastructure Requirements

**Development Environment**:
- CPU: 8+ cores
- RAM: 32GB minimum
- GPU: NVIDIA GPU with 8GB+ VRAM (for Module 9)
- Storage: 500GB SSD

**Production Environment**:
- CPU: 16+ cores
- RAM: 64GB minimum
- GPU: NVIDIA A100 or equivalent (for acceleration)
- Storage: 2TB NVMe SSD
- Network: 10Gbps

### External Dependencies

**APIs & Services**:
- Google Gemini API (https://ai.google.dev)
  - gemini-3-pro-preview access
  - gemini-1.5-flash access
  - gemini-embedding-001 access
- OpenAI API (for gpt-4o-mini) (https://platform.openai.com)
- Optional: Anthropic API (for Claude)

**Software Dependencies**:
- Agno framework latest (https://github.com/agno-agi/agno)
- SurrealDB 2.0+ (https://surrealdb.com/install)
- Redis 7+ (https://redis.io/download)
- Python 3.11+ (https://www.python.org/downloads/)
- CUDA Toolkit 12+ (https://developer.nvidia.com/cuda-downloads)
- ONNX Runtime GPU (https://onnxruntime.ai/)

---

## SUCCESS METRICS

### Technical Metrics

**Performance Targets**:
- Search latency p95: <100ms
- Search latency p99: <200ms
- Embedding generation: >1000 per second (with GPU)
- Memory precision@5: >90%
- Memory precision@10: >85%
- Cache hit rate L1: >70%
- Cache hit rate L2: >80%
- Consolidation time: <5 min for 10k memories

**Quality Targets**:
- Verification pass rate: >70%
- Deduplication accuracy: >90%
- Entity extraction accuracy: >85%
- Debate consensus agreement: >80%
- False positive rate: <5%

**Cost Targets**:
- LLM cost per memory: <$0.03 (down from $0.20)
- Monthly LLM cost: <$500 (for 1M memories)
- Total cost reduction: >85%

**Reliability Targets**:
- System uptime: >99.95%
- Database availability: >99.99%
- Error rate: <0.1%
- Memory loss rate: <0.01%

### Business Metrics

**Adoption Metrics**:
- Template agent successfully cloned: 5+ times
- Production deployments: 2+ instances
- Community contributions: 10+ external PRs
- Documentation usage: 100+ page views/month

**Productivity Metrics**:
- Time to create new agent: <2 hours (vs 2 weeks)
- Agent development cost: -95%
- Maintenance overhead: -80%
- Code reuse: >90%

---

## RISK MANAGEMENT

### Technical Risks

**Risk #1: SurrealDB Performance at Scale**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Extensive load testing, query optimization, distributed setup if needed
- **Contingency**: Fallback to PostgreSQL + pgvector

**Risk #2: Gemini API Rate Limits**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: LLM cascading, caching, rate limit handling
- **Contingency**: Multi-provider setup (Gemini + OpenAI + Anthropic)

**Risk #3: GPU Availability**
- **Probability**: Low
- **Impact**: Low (GPU is optimization, not requirement)
- **Mitigation**: CPU fallback for all operations
- **Contingency**: Cloud GPU rental (AWS/GCP)

**Risk #4: Memory Complexity**
- **Probability**: High
- **Impact**: Medium
- **Mitigation**: Modular implementation, extensive documentation, test coverage >80%
- **Contingency**: Phase out complex features if needed

### Project Risks

**Risk #5: Scope Creep**
- **Probability**: High
- **Impact**: High
- **Mitigation**: Strict scope control, modular design allows deferred features
- **Contingency**: Drop advanced features (strategies 35-57) if timeline critical

**Risk #6: Resource Availability**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Cross-training, documentation, modular architecture
- **Contingency**: Community engagement, open-source contributions

**Risk #7: Integration Failures**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Integration tests, mock services, gradual integration
- **Contingency**: Simplified integration points

---

## QUALITY ASSURANCE

### Testing Strategy

**Unit Testing**: >80% code coverage
- All domain logic tested
- Mock external dependencies
- Property-based testing for critical paths

**Integration Testing**: Complete workflow coverage
- End-to-end agent workflows
- Database integration
- API integration
- Multi-agent coordination

**Load Testing**: Scale validation
- 100k memories: <500ms/query
- 1M memories: <1s/query
- 10 concurrent agents
- 1000 concurrent users (simulation)

**Performance Testing**: Benchmark validation
- All performance metrics validated
- Latency distributions (p50, p95, p99)
- Resource utilization monitoring
- Cost tracking validation

### Code Quality Standards

**Python Standards**:
- PEP 8 compliance
- Type hints (mypy strict mode)
- Docstrings (Google style)
- No circular dependencies
- Maximum function complexity: 10

**Documentation Standards**:
- All public APIs documented
- Architecture decisions recorded (ADRs)
- Runbooks for operations
- Troubleshooting guides

**Security Standards**:
- Input validation on all endpoints
- SQL injection prevention (parameterized queries)
- API key rotation support
- Rate limiting
- OWASP compliance

---

## DEPLOYMENT STRATEGY

### Deployment Models

**Development Deployment**:
- Local SurrealDB instance
- Local Redis instance
- Mock LLM calls for testing
- Minimal resource requirements

**Staging Deployment**:
- Cloud SurrealDB (Docker)
- Cloud Redis
- Real LLM calls with budget limits
- Production-like environment

**Production Deployment**:
- High-availability SurrealDB cluster
- Redis cluster
- GPU-accelerated nodes
- Monitoring & alerting
- Backup & disaster recovery

### Deployment Checklist

**Pre-Deployment**:
- [ ] All tests passing (unit + integration + load)
- [ ] Documentation complete
- [ ] Security audit complete
- [ ] Performance benchmarks met
- [ ] Backup strategy validated
- [ ] Monitoring configured
- [ ] Runbooks prepared

**Deployment**:
- [ ] Database migration executed
- [ ] Configuration deployed
- [ ] Application deployed (canary 5% → 100%)
- [ ] Health checks passing
- [ ] Monitoring active

**Post-Deployment**:
- [ ] Smoke tests passing
- [ ] Performance monitoring
- [ ] Error rate monitoring
- [ ] User feedback collection
- [ ] Incident response ready

---

## TIMELINE & MILESTONES

**Note**: Timeline managed by team, not specified in plan

### Milestones

**M1: Foundation Complete**
- Module 1 complete
- Database operational
- Basic CRUD working
- **Deliverable**: Working database with test data

**M2: Search System Complete**
- Modules 1, 2 complete
- Hybrid search working
- Intent classification active
- **Deliverable**: Searchable memory system

**M3: Memory Lifecycle Complete**
- Modules 1, 2, 3 complete
- 3-tier hierarchy working
- Consolidation active
- **Deliverable**: Self-managing memory system

**M4: Core Features Complete (22 strategies)**
- Modules 1-5 complete
- All core features working
- MCP interface active
- **Deliverable**: Functional baseline agent

**M5: Cost Optimization Complete**
- Modules 1-6 complete
- LLM cascading working
- Cost reduction validated
- **Deliverable**: Cost-optimized agent

**M6: Quality Assurance Complete**
- Modules 1-7 complete
- Verification gates active
- Multi-agent debate working
- **Deliverable**: High-quality agent

**M7: Production Features Complete**
- Modules 1-9 complete
- Audit logging active
- GPU acceleration working
- **Deliverable**: Production-ready agent

**M8: Full Implementation Complete (57 strategies)**
- All 10 modules complete
- Multimodal working
- Dashboards deployed
- **Deliverable**: Complete template agent

---

## DOCUMENTATION REQUIREMENTS

### Required Documentation

**Technical Documentation**:
1. Architecture documentation (this series: 01-plan.md, 02-tasks.md, 03-architecture.md, etc.)
2. API documentation (auto-generated + manual)
3. Database schema documentation
4. Code documentation (docstrings)
5. Integration guides

**Operational Documentation**:
6. Installation guide
7. Configuration guide
8. Deployment guide
9. Monitoring guide
10. Troubleshooting guide
11. Runbooks (incident response)

**User Documentation**:
12. User guide
13. Template usage guide
14. Example use cases
15. FAQ

**Developer Documentation**:
16. Contributing guide
17. Development setup
18. Testing guide
19. Module documentation
20. ADRs (Architecture Decision Records)

### Documentation Standards

**Format**: Markdown (.md files)  
**Structure**: Numbered files (01-plan.md, 02-tasks.md, etc.)  
**Version Control**: Git (all docs in repo)  
**Auto-Generation**: Sphinx for API docs  
**Diagrams**: Mermaid.js for all diagrams  

---

## REFERENCES

### Official Documentation
- Agno Framework: https://docs.agno.com
- SurrealDB: https://surrealdb.com/docs
- Gemini API: https://ai.google.dev/docs
- Redis: https://redis.io/docs

### Research Papers
- LLM Agent Memory: https://arxiv.org/abs/2308.00352
- Hybrid Retrieval: https://arxiv.org/abs/2310.03094
- Multi-Agent Systems: https://arxiv.org/abs/2309.07864
- Graph-Based Memory: https://arxiv.org/abs/2310.10108

### Related Projects
- Mem0: https://github.com/mem0ai/mem0
- DevContext MCP: https://github.com/aiurda/devcontext
- Redis Agent Memory: https://github.com/redis-projects/agent-memory-server
- MCP Memory Service: https://github.com/doobidoo/mcp-memory-service

### Internal References
- Previous Analysis: KHALA_IMPROVEMENTS_ANALYSIS.md
- Strategy Summary: KHALA_IMPROVEMENTS_SUMMARY.md
- Original Guide: implementation-guide-complete.md
- Checklist: IMPLEMENTATION_CHECKLIST.md

---

## APPROVAL & SIGN-OFF

**Plan Prepared By**: AI Research Team  
**Date**: November 2025  
**Status**: ✅ Complete and Ready for Implementation

**Next Steps**:
1. Review this plan with team
2. Proceed to 02-tasks.md for detailed task breakdown
3. Review 03-architecture.md for technical specifications
4. Begin Module 1 implementation

---

**END OF 01-PLAN.MD**
