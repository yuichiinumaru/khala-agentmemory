# RECEITA IDEAL: SISTEMA DE MEMÓRIA DE AGENTES DE PRÓXIMA GERAÇÃO (v2.0)
## Síntese Otimizada de 15 Repositórios + Análise Profunda de 25+ Técnicas

---

## VISÃO GERAL EXECUTIVA

Este documento define a arquitetura completa de um sistema de memória para agentes de IA que **combina as melhores técnicas** de todos os 15 repositórios analisados, otimizando para:

- **Performance**: Latência <100ms para busca (p95)
- **Precisão**: Precision@5 >85% em retrieval
- **Escalabilidade**: Suporte a milhões de memórias
- **Flexibilidade**: Multi-backend, multi-estratégia
- **Custo**: Operação eficiente com otimizações offline
- **Inteligência**: Consolidação autônoma + LLM-assistida

---

## ARQUITETURA MULTI-CAMADA

### 1. CAMADA DE ARMAZENAMENTO PRIMÁRIO (Hybrid Local + Cloud)

#### 1.1 Storage Local (Desenvolvimento/Single-Device)
```
SQLite-vec (ou DuckDB)
├── Embeddings nativo (ONNX Runtime)
├── Full-text search
├── HNSW index (M=16, efConstruction=200, efRuntime=50)
└── Latência: 5-10ms
```

**Configuração**:
- SQLite com WAL mode (concorrência)
- Prepared statements (query caching)
- Connection pool (min: 1, max: 5)
- Batch operations para writes

#### 1.2 Storage Cloud (Backup/Multi-Device)
```
Cloudflare D1 + Vectorize (Primary)
├── Backup automático
├── Sincronização assíncrona
├── Edge distribution global
└── Multi-tenancy nativa

OU

Supabase pgvector (Alternativa)
├── PostgreSQL nativo
├── HNSW ou IVFFlat automático
└── Backup gerenciado
```

#### 1.3 Graph Store (Relacionamentos)
```
Neo4j (Produção)
├── Temporal edges (timestamps)
├── Multi-hop reasoning
├── Pattern matching (Cypher)
└── Escalável para bilhões de relações

OU

SQLite Graph Extension (Lightweight)
├── Para projetos simples
└── Zero overhead
```

---

## CAMADA 2: MEMÓRIA HIERÁRQUICA (3-Tier)

### Working Memory (Sessão)
```
┌─────────────────────────────────────────┐
│ WORKING MEMORY (Redis / In-Memory)      │
│ - TTL: Duração da sessão (até 1h)      │
│ - Último N mensagens: 20-50             │
│ - Cache embeddings: LRU(1000)           │
│ - Latência: 1-5ms                       │
│                                         │
│ Estrutura:                              │
│ {                                       │
│   session_id: UUID,                     │
│   messages: [],          # Convo ativa   │
│   memories: [],          # Discrete     │
│   data: {},              # JSON flex     │
│   metadata: {            # Tracking      │
│     last_accessed: ts,                  │
│     topics: [],                         │
│     entities: []                        │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
      ↓ (PROMOTION: idade > 10 min OU count > 30)
```

### Short-Term Memory (Recente)
```
┌─────────────────────────────────────────┐
│ SHORT-TERM MEMORY (Vector DB Local)     │
│ - TTL: 7-30 dias                        │
│ - Memórias "quentes"                    │
│ - Ativos/em-edição                      │
│ - Projetos correntes                    │
│ - Latência: 10-50ms                     │
│                                         │
│ Otimizações:                            │
│ - Índices agressivos (M=20)             │
│ - Compressão mínima                     │
│ - Recency boost em busca                │
└─────────────────────────────────────────┘
      ↓ (CONSOLIDATION: semanal/monthly)
```

### Long-Term Memory (Persistente)
```
┌─────────────────────────────────────────┐
│ LONG-TERM MEMORY (Vector DB + Graph)    │
│ - TTL: Indefinido                       │
│ - Conhecimento consolidado              │
│ - Decisões + Milestones                 │
│ - Grafo de relacionamentos              │
│ - Latência: 50-200ms                    │
│                                         │
│ Estratégia de Compactação:              │
│ - Merge semelhantes (>0.95 similarity)  │
│ - Archive antigos (<0.2 relevância)     │
│ - Compress clusters (TF-IDF)            │
└─────────────────────────────────────────┘
```

---

## CAMADA 3: SISTEMA DE EMBEDDINGS ADAPTÁVEL

### 3.1 Estratégia Dual-Model

```
PRIMARY_MODEL = "bge-large-en-v1.5"
├── Dimensões: 1024
├── Performance: Balanceado
├── Uso: Busca, reranking

LIGHTWEIGHT_MODEL = "all-MiniLM-L6-v2"
├── Dimensões: 384
├── Performance: Ultra-rápido
├── Uso: Development, local
├── ONNX Runtime (sem PyTorch)
```

### 3.2 Specialized Models (Opcional)

```
code_model = "codebert"       # Para code snippets
query_model = "bge-m3"        # Para queries complexas
multimodal = "clip"           # Para imagens + texto
```

### 3.3 Cache Multi-Nível

```
L1: In-Memory LRU Cache
    ├── Capacidade: 1000 embeddings
    ├── Política: LRU
    ├── Latência: <1ms
    ├── TTL: Sessão
    └── Hit rate objetivo: >70%

L2: Redis Cache (Distributed)
    ├── Capacidade: 10k embeddings
    ├── TTL: 24 horas
    ├── Latência: 5-10ms
    └── Hit rate objetivo: >80%

L3: Persistente
    ├── Vector DB
    ├── Latência: 50-200ms
    └── Hit rate: 100% (fallback)
```

### 3.4 Generation Strategy

```python
async def generate_embeddings_batch(texts: List[str]):
    """Geração assíncrona em batches"""
    batch_size = 16  # Otimizado
    for batch in chunks(texts, batch_size):
        embeddings = await model.encode(batch)
        # Cache L1
        for text, emb in zip(batch, embeddings):
            cache_l1.put(text, emb)
        # Queue para L2/L3
        await queue_for_persistence(batch, embeddings)
```

---

## CAMADA 4: SISTEMA DE BUSCA AVANÇADA

### 4.1 Pipeline Multi-Stage (Recomendado para Produção)

```
USER QUERY
    ↓
[1] QUERY OPTIMIZATION
    - Expande siglas/contexto
    - Detecta negações
    - Normaliza espaçamento
    ↓
[2] EMBEDDING GENERATION
    - Usa cache L1 se disponível
    - Gera novo se necessário
    ↓
[3] ANN SEARCH (HNSW)
    - K=100 (top candidates)
    - Distance metric: COSINE
    ↓
[4] KEYWORD FILTERING (BM25)
    - Reduz para K=50
    - Ordena por relevância
    ↓
[5] METADATA FILTERING
    - Filtra por: user_id, namespace, timestamp, tags
    - Reduz para K=20
    - Apply recency weighting
    ↓
[6] RERANKING (Cross-Encoder)
    - Usa modelo especializado
    - Reduz para K=5-10
    - Precision@5 >85%
    ↓
RESULTADO FINAL
```

**Latência Esperada**:
- Stages 1-3: 50ms (parallelizável)
- Stage 4-5: 30ms
- Stage 6: 20ms
- **Total: ~100ms (p95)**

### 4.2 Busca Simples (Speed-Optimized)

```
USER QUERY → EMBEDDING → ANN SEARCH → FILTERS → RESULTS
                          (Top 10 direto)
Latência: 30-50ms
```

### 4.3 Adaptive Retrieval

```python
def adaptive_retrieval(query: str, context: Dict) -> List[Memory]:
    """Seleciona strategy baseado em contexto"""
    
    if is_recent_conversation(context):
        # Busca recente
        return working_memory.get_recent(limit=20)
    
    elif is_code_related(query):
        # Busca híbrida: semântica + graph
        semantic = semantic_search(query, k=10)
        graph = graph_search(entities=extract_entities(query))
        return merge_ranked(semantic, graph)
    
    elif is_decision_query(query):
        # Busca em long-term com filtro
        return long_term.search(
            query=query,
            filter={"category": "decision", "importance": "high"}
        )
    
    else:
        # Busca padrão multi-stage
        return multi_stage_search(query)
```

---

## CAMADA 5: CONSOLIDAÇÃO E PROCESSAMENTO BACKGROUND

### 5.1 Dream-Inspired Autonomous Processing (0% LLM)

```
DAILY (3 AM - 5 minutos):
├── Atualizar relevance scores (decay exponencial)
├── Encontrar associações criativas (similaridade 0.3-0.7)
├── Operações: puro math, zero LLM
└── Custo: ~$0

WEEKLY (4 AM - 20 minutos):
├── Cluster memórias por embedding similarity
├── Semantic compression (TF-IDF + centroid)
├── Começar compactação de clusters antigos
├── Custo: ~$0

MONTHLY (5 AM - 1 hora):
├── Recalcular todos os relevance scores
├── Controlled forgetting (archive antigos)
├── Crear month-level semantic summaries
├── Garbage collection
└── Custo: ~$0

QUARTERLY (6 AM - 3 horas):
├── Padrão extraction long-term
├── Reorganizar grafo (otimizar índices)
├── Year-level knowledge maps
└── Custo: ~$0
```

### 5.2 LLM-Assisted Enhancement (Optional)

```
QUANDO: Após processamento autônomo
ONDE: Apenas para clusters significativos (>5 memórias)

Tarefas LLM:
├── Gerar narrativas naturais (sumários prose)
├── Extrair insights criativos (associações)
└── Classificar importância relativa

Custo: ~$0.10-0.50/mês (muito seletivo)
```

### 5.3 Extraction Strategy (Redis Agent Style)

```
ON WORKING_MEMORY_PROMOTION:
├── [STRATEGY: discrete] Extrair fatos individuais
├── [STRATEGY: summary] Criar sumários conversas longas
├── [STRATEGY: preferences] Focar em preferências
└── [STRATEGY: custom] Domain-specific (legal/médico)

Configuração:
strategy_type = "discrete"  # Default, mais rápido
strategy_config = {
    "max_memories_per_extraction": 10,
    "min_importance_score": 0.5,
    "extraction_model": "gpt-4o-mini"  # Rápido
}
```

---

## CAMADA 6: DEDUPLICAÇÃO HÍBRIDA

### 6.1 Hash-Based (Rápido, Exato)
```python
def hash_dedup(memory: Memory):
    """O(1), detecta duplicatas exatas"""
    hash = SHA256(memory.text)
    if hash in deduplicated_set:
        return "SKIP"  # Idêntico
    deduplicated_set.add(hash)
    return "KEEP"
```

### 6.2 Semantic Dedup (Préciso, Custoso)
```python
async def semantic_dedup(memory: Memory, existing: List[Memory]):
    """O(n log n), detecta similares"""
    for existing_mem in existing:
        similarity = cosine_similarity(
            memory.embedding, 
            existing_mem.embedding
        )
        if similarity > 0.95:
            # Merge com LLM
            merged = await merge_memories(memory, existing_mem)
            return "MERGE", merged
    return "KEEP", memory
```

### 6.3 Estratégia Híbrida (Recomendada)
```python
async def hybrid_dedup(memory: Memory):
    """Hash primeiro (rápido), depois semantic (seletivo)"""
    
    # Fase 1: Hash (O(1))
    if hash_dedup(memory) == "SKIP":
        return "DUPLICATE"
    
    # Fase 2: Semantic (apenas se config permitir)
    if should_check_semantic(memory.importance):
        existing = await search_similar(memory, k=5)
        if existing:
            result, merged = await semantic_dedup(memory, existing)
            return result, merged
    
    return "NEW", memory
```

---

## CAMADA 7: AGENTES ESPECIALIZADOS

### 7.1 Coordenador de Agentes

```python
class AgentCoordinator:
    """Orquestra 4 agentes especializados"""
    
    agents = {
        "analyzer":    AnalyzerAgent(),      # Padrões
        "synthesizer": SynthesizerAgent(),   # Sumários
        "retriever":   RetrieverAgent(),     # Busca otimizada
        "curator":     CuratorAgent()        # Qualidade
    }
    
    async def process_task(task: Task):
        # Delegação inteligente
        agent = self.select_agent(task)
        return await agent.process(task)
```

### 7.2 Função de Cada Agente

| Agente | Função | Gatilho | Custo |
|--------|--------|---------|-------|
| Analyzer | Extrair padrões, correlações | Weekly | Baixo |
| Synthesizer | Gerar sumários, narrativas | On-demand | Médio |
| Retriever | Otimizar busca, ranking | Per-query | Médio |
| Curator | Validação, limpeza | Daily | Baixo |

---

## CAMADA 8: GRAFO DE CONHECIMENTO TEMPORAL

### 8.1 Estrutura

```
NODE (Temporal)
├── id: UUID
├── type: "concept" | "decision" | "entity" | "event"
├── text: str
├── embedding: [1024]
├── created_at: timestamp
├── updated_at: timestamp
├── accessed_at: timestamp
├── importance: float (0-1)
└── metadata: {}

EDGE (Directed, Versioned)
├── source_id: UUID
├── target_id: UUID
├── relation_type: "related_to" | "caused_by" | "part_of" | ...
├── created_at: timestamp
├── weight: float (similarity score)
├── is_active: bool (soft-delete)
└── confidence: float (0-1)
```

### 8.2 Queries Cypher (Neo4j)

```cypher
-- Busca multi-hop
MATCH (user:User) -[:DISCUSSED]-> (topic:Topic) 
      -[:RELATED_TO]-> (solution:Solution)
WHERE user.id = $userId AND topic.created_at > $since
RETURN solution ORDER BY solution.importance DESC

-- Path reasoning
MATCH p = shortestPath((start:Decision) -[*..3]-> (end:Decision))
WHERE start.id = $startId AND end.id = $endId
RETURN p, length(p) as hops
```

---

## CAMADA 9: OBSERVABILIDADE E MANUTENÇÃO

### 9.1 Health Checks

```python
async def check_system_health():
    return {
        "memory_count": {
            "working": get_working_count(),
            "short_term": get_shortterm_count(),
            "long_term": get_longterm_count()
        },
        "vector_index_health": {
            "fragmentation": calculate_fragmentation(),
            "avg_degree": calculate_avg_degree()  # HNSW M
        },
        "cache_stats": {
            "l1_hit_rate": cache_l1.hit_rate(),
            "l2_hit_rate": cache_l2.hit_rate()
        },
        "performance": {
            "avg_retrieval_time_ms": metrics.avg_latency,
            "p95_retrieval_time_ms": metrics.p95_latency,
            "p99_retrieval_time_ms": metrics.p99_latency
        },
        "storage": {
            "size_mb": get_db_size() / 1024 / 1024,
            "compression_ratio": calculate_compression()
        },
        "background": {
            "last_consolidation": get_last_consolidation_time(),
            "next_scheduled": get_next_consolidation_time(),
            "pending_tasks": count_pending_tasks()
        }
    }
```

### 9.2 Alertas

```yaml
alerts:
  memory_growth_alert:
    condition: "daily_growth_rate > 10%"
    action: "trigger_aggressive_compaction"
  
  cache_hit_rate_low:
    condition: "l1_hit_rate < 50%"
    action: "increase_l1_size or review_queries"
  
  latency_degradation:
    condition: "p95_latency > 200ms"
    action: "rebuild_indices or optimize_queries"
  
  index_fragmentation:
    condition: "fragmentation > 30%"
    action: "rebuild_hnsw"
```

---

## STACK TECNOLÓGICO RECOMENDADO

### Core
```
Vector DB:          Qdrant (prod) ou Supabase pgvector (simples)
Local Storage:      SQLite-vec com ONNX Runtime
Graph DB:           Neo4j (prod) ou SQLite graph (dev)
Cache:              Redis (distributed) ou in-memory (local)
Task Queue:         Docket (Redis-based)
```

### Embeddings
```
Primary:            bge-large-en-v1.5 (HuggingFace)
Lightweight:        all-MiniLM-L6-v2 (ONNX)
API Fallback:       OpenAI text-embedding-3-small
```

### Processing
```
NER:                spaCy (BERT-based)
Topic Modeling:     BERTopic ou sklearn
Summarization:      LLM (Claude 3.5 Haiku ou GPT-4o-mini)
Reranking:          Cross-Encoder (MSMARCO) ou LLM
```

### Framework
```
Backend:            FastAPI (Python) ou Express (Node.js)
MCP:                @modelcontextprotocol/sdk
Async:              asyncio / uvloop
Monitoring:         Prometheus + Grafana (opcional)
```

---

## CONFIGURAÇÃO RECOMENDADA PARA PRODUÇÃO

```yaml
memory_configuration:
  storage:
    local:
      type: "sqlite-vec"
      wal_mode: true
      connection_pool: {min: 2, max: 5}
    cloud:
      type: "cloudflare-d1"
      sync_interval_minutes: 5
      backup_enabled: true
  
  hierarchy:
    working_memory:
      ttl_minutes: 60
      max_messages: 50
      promotion_age_minutes: 10
    short_term:
      ttl_days: 15
      retention_policy: "keep_active"
    long_term:
      ttl_days: null  # Indefinido
      compaction: true
  
  embeddings:
    model: "bge-large-en-v1.5"
    dimensions: 1024
    cache_l1_size: 1000
    cache_l2_ttl_hours: 24
    batch_generation_size: 16
  
  retrieval:
    strategy: "multi_stage"
    hnsw_config:
      m: 16
      ef_construction: 200
      ef_runtime: 50
    reranking_enabled: true
    recency_boost: true
    min_relevance_score: 0.5
  
  background:
    consolidation:
      daily: true
      daily_time: "03:00"
      weekly: true
      weekly_time: "04:00"
      monthly: true
      monthly_time: "05:00"
    deduplication:
      enabled: true
      semantic_threshold: 0.95
      archive_enabled: true
    compaction:
      enabled: true
      interval_days: 7
      compression_ratio: 0.6
```

---

## MÉTRICAS DE SUCESSO

### Performance
- Latência busca: **<100ms (p95)**
- Throughput indexing: **>1000 embeddings/s**
- Cache hit rate: **>70% (L1), >80% (L2)**

### Qualidade
- Precision@5: **>85%**
- Recall@10: **>80%**
- Deduplication accuracy: **>95%**

### Eficiência
- Compression ratio: **>0.7** (70% redução)
- Storage per memory: **<1KB** (média)
- LLM cost: **<$1/1M memories**

### Escalabilidade
- Suporte a: **>10M memórias**
- Growth sustainability: **>5 anos**
- Index fragmentation: **<20%**

---

## ROADMAP DE IMPLEMENTAÇÃO

### Phase 1: Foundation (Semana 1-2)
- [x] SQLite-vec local storage
- [x] BGE embeddings + ONNX
- [x] HNSW indexing
- [x] Basic retrieval

### Phase 2: Enhancement (Semana 3-4)
- [x] Multi-stage search
- [x] Working ↔ Long-term promotion
- [x] Hash deduplication
- [x] Cache multi-nível

### Phase 3: Intelligence (Semana 5-8)
- [x] Dream-inspired consolidation
- [x] Graph storage (Neo4j)
- [x] Semantic deduplication
- [x] Extraction strategies

### Phase 4: Optimization (Semana 9-12)
- [x] Cross-encoder reranking
- [x] Agent coordination
- [x] Advanced observability
- [x] Cloud sync (Cloudflare)

### Phase 5: Production (Semana 13+)
- [x] Load testing (10M memories)
- [x] Security hardening
- [x] MCP interface
- [x] Documentation completa

---

## CONCLUSÃO

Esta receita combina o melhor de:
✓ **Mem0**: Flexibilidade de backends + 19+ vector stores
✓ **MCP Memory Service**: Consolidação dream-inspired autônoma
✓ **Redis Agent**: Multi-estratégia de extraction + background tasks
✓ **MemMachine**: Arquitetura limpa + PostgreSQL confiável
✓ **Agent-MCP**: Colaboração multi-agente + visualização
✓ **Todos os outros**: Insights específicos em busca, caching, observabilidade

**Resultado Final**: Sistema robusto, escalável, inteligente e eficiente que rivaliza com soluções comerciais de ponta, mas completamente open-source e customizável.

---

**Versão**: 2.0 | **Data**: Novembro 2025 | **Status**: Production-Ready
**Baseado em análise de**: 15 repositórios, 25+ técnicas, 100+ sources
