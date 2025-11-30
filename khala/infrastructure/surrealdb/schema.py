"""SurrealDB database schema for KHALA memory system.

This module contains the complete SurrealDB schema definition
including tables, indexes, functions, and permissions.
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseSchema:
    """Database schema manager for KHALA."""
    
    # Schema definition matching the KHALA documentation
    SCHEMA_DEFINITIONS = {
        # Namespace and database setup
        "namespace": "DEFINE NAMESPACE khala;",
        "database": "DEFINE DATABASE memories;",
        
        # Memory table with all fields
        "memory_table": """
        DEFINE TABLE memory SCHEMAFULL;
        
        -- Core fields
        DEFINE FIELD id ON memory TYPE string;
        DEFINE FIELD user_id ON memory TYPE string;
        DEFINE FIELD content ON memory TYPE string;
        DEFINE FIELD content_hash ON memory TYPE string;
        DEFINE FIELD embedding ON memory TYPE array<float> FLEXIBLE;
        DEFINE FIELD tier ON memory TYPE enum<working,short_term,long_term>;
        DEFINE FIELD importance ON memory TYPE float;
        DEFINE FIELD tags ON memory TYPE array<string>;
        DEFINE FIELD category ON memory TYPE string;
        DEFINE FIELD summary ON memory TYPE string;
        DEFINE FIELD metadata ON memory TYPE object FLEXIBLE;
        
        -- Timestamps
        DEFINE FIELD created_at ON memory TYPE datetime;
        DEFINE FIELD updated_at ON memory TYPE datetime;
        DEFINE FIELD accessed_at ON memory TYPE datetime;
        
        -- Usage tracking
        DEFINE FIELD access_count ON memory TYPE int DEFAULT 0;
        DEFINE FIELD llm_cost ON memory TYPE float DEFAULT 0.0;
        DEFINE FIELD verification_score ON memory TYPE float;
        DEFINE FIELD verification_issues ON memory TYPE array<string>;
        DEFINE FIELD debate_consensus ON memory TYPE object FLEXIBLE;
        DEFINE FIELD is_archived ON memory TYPE bool DEFAULT false;
        DEFINE FIELD decay_score ON memory TYPE float;
        
        -- Tier 6: Advanced Metadata
        DEFINE FIELD source ON memory TYPE object FLEXIBLE;
        DEFINE FIELD sentiment ON memory TYPE object FLEXIBLE;
        """,
        
        # Memory indexes
        "memory_indexes": """
        -- Primary index (multi-tenancy)
        DEFINE INDEX user_index ON memory FIELDS user_id;
        
        -- Deduplication index
        DEFINE INDEX content_hash_index ON memory FIELDS content_hash;

        -- Search indexes
        DEFINE INDEX vector_search ON memory FIELDS embedding HNSW 
          PARAMETERS {
            M: 16,
            ef_construction: 200,
            ef_runtime: 50,
            dimensions: 768,
            distance_metric: "cosine"
          };
        
        DEFINE INDEX bm25_search ON memory FIELDS content FULLTEXT;
        
        -- Performance indexes
        DEFINE INDEX tier_index ON memory FIELDS tier;
        DEFINE INDEX importance_index ON memory FIELDS importance DESC;
        DEFINE INDEX created_index ON memory FIELDS created_at DESC;
        DEFINE INDEX accessed_index ON memory FIELDS accessed_at DESC;
        
        -- Hot path composite
        DEFINE INDEX hot_path ON memory 
          FIELDS user_id, importance DESC, EXPRESSION (now() - accessed_at);
        
        -- Tag prefix search
        DEFINE INDEX tag_search ON memory FIELDS tags FULLTEXT;
        """,
        
        # Entity table
        "entity_table": """
        DEFINE TABLE entity SCHEMAFULL;
        
        DEFINE FIELD id ON entity TYPE string;
        DEFINE FIELD text ON entity TYPE string;
        DEFINE FIELD entity_type ON entity TYPE string;
        DEFINE FIELD confidence ON entity TYPE float;
        DEFINE FIELD embedding ON entity TYPE array<float> FLEXIBLE;
        DEFINE FIELD metadata ON entity TYPE object FLEXIBLE;
        DEFINE FIELD created_at ON entity TYPE datetime;
        
        -- Indexes
        DEFINE INDEX entity_text_index ON entity FIELDS text;
        DEFINE INDEX entity_type_index ON entity FIELDS entity_type;
        DEFINE INDEX entity_confidence_index ON entity FIELDS confidence DESC;
        DEFINE INDEX entity_vector_index ON entity FIELDS embedding HNSW 
          PARAMETERS {
            M: 16,
            ef_construction: 200,
            ef_runtime: 50,
            dimensions: 768,
            distance_metric: "cosine"
          };
        """,
        
        # Relationship table (graph edge)
        "relationship_table": """
        DEFINE TABLE relationship SCHEMAFULL;
        
        DEFINE FIELD from_entity_id ON relationship TYPE string;
        DEFINE FIELD to_entity_id ON relationship TYPE string;
        DEFINE FIELD relation_type ON relationship TYPE string;
        DEFINE FIELD strength ON relationship TYPE float;
        DEFINE FIELD valid_from ON relationship TYPE datetime;
        DEFINE FIELD valid_to ON relationship TYPE datetime;
        DEFINE FIELD transaction_time_start ON relationship TYPE datetime;
        DEFINE FIELD transaction_time_end ON relationship TYPE datetime;
        DEFINE FIELD created_at ON relationship TYPE datetime;
        
        -- Indexes
        DEFINE INDEX rel_from_index ON relationship FIELDS from_entity_id;
        DEFINE INDEX rel_to_index ON relationship FIELDS to_entity_id;
        DEFINE INDEX rel_type_index ON relationship FIELDS relation_type;
        DEFINE INDEX rel_strength_index ON relationship FIELDS strength DESC;
        """,
        
        # Audit log table
        "audit_log_table": """
        DEFINE TABLE audit_log SCHEMAFULL;
        
        DEFINE FIELD id ON audit_log TYPE string;
        DEFINE FIELD timestamp ON audit_log TYPE datetime DEFAULT time::now();
        DEFINE FIELD user_id ON audit_log TYPE string;
        DEFINE ENTITY action ON audit_log NATURE DATA;
        DEFINE FIELD memory_id ON audit_log TYPE string;
        DEFINE FIELD agent_id ON audit_log TYPE string;
        DEFINE FIELD operation ON audit_log TYPE string;
        DEFINE FIELD reason ON audit_log TYPE string;
        DEFINE FIELD before_state ON audit_log TYPE object FLEXIBLE;
        DEFINE FIELD after_state ON audit_log TYPE object FLEXIBLE;
        
        -- Indexes
        DEFINE INDEX audit_time_index ON audit_log FIELDS timestamp DESC;
        DEFINE INDEX audit_user_index ON audit_log FIELDS user_id;
        DEFINE INDEX audit_memory_index ON audit_log FIELDS memory_id;
        """,

        # Search Session table
        "search_session_table": """
        DEFINE TABLE search_session SCHEMAFULL;

        DEFINE FIELD id ON search_session TYPE string;
        DEFINE FIELD user_id ON search_session TYPE string;
        DEFINE FIELD query ON search_session TYPE string;
        DEFINE FIELD expanded_queries ON search_session TYPE array<string>;
        DEFINE FIELD filters ON search_session TYPE object FLEXIBLE;
        DEFINE FIELD timestamp ON search_session TYPE datetime DEFAULT time::now();
        DEFINE FIELD results_count ON search_session TYPE int DEFAULT 0;
        DEFINE FIELD metadata ON search_session TYPE object FLEXIBLE;

        -- Indexes
        DEFINE INDEX session_user_index ON search_session FIELDS user_id;
        DEFINE INDEX session_time_index ON search_session FIELDS timestamp DESC;
        """,

        # Skill table
        "skill_table": """
        DEFINE TABLE skill SCHEMAFULL;
        DEFINE FIELD name ON skill TYPE string;
        DEFINE FIELD code ON skill TYPE string;
        DEFINE FIELD description ON skill TYPE string;
        DEFINE FIELD usage_count ON skill TYPE int DEFAULT 0;
        DEFINE FIELD success_rate ON skill TYPE float DEFAULT 0.0;
        DEFINE FIELD language ON skill TYPE string;
        DEFINE FIELD skill_type ON skill TYPE string;
        DEFINE FIELD parameters ON skill TYPE array<object>;
        DEFINE FIELD return_type ON skill TYPE string;
        DEFINE FIELD dependencies ON skill TYPE array<string>;
        DEFINE FIELD tags ON skill TYPE array<string>;
        DEFINE FIELD metadata ON skill TYPE object FLEXIBLE;
        DEFINE FIELD embedding ON skill TYPE array<float>;
        DEFINE FIELD created_at ON skill TYPE datetime;
        DEFINE FIELD updated_at ON skill TYPE datetime;
        DEFINE FIELD version ON skill TYPE string;
        DEFINE FIELD is_active ON skill TYPE bool;
        """,
        
        # Custom functions
        "functions": """
        -- Decay score calculation function
        DEFINE FUNCTION fn::decay_score(age_days float, original_importance float, half_life_days float DEFAULT 30.0) {
            RETURN original_importance * math::exp(-age_days / half_life_days);
        };
        
        -- Memory promotion check function
        DEFINE FUNCTION fn::should_promote(tier string, age_hours float, access_count int, importance float) {
            IF tier = 'working' AND age_hours > 0.5 AND access_count > 5 AND importance > 0.8 {
                RETURN true;
            } ELSIF tier = 'short_term' AND (age_hours > 360 OR importance > 0.9) {
                RETURN true;
            } ELSE {
                RETURN false;
            };
        };
        
        -- Memory archival check function
        DEFINE FUNCTION fn::should_archive(age_hours float, access_count int, importance float) {
            IF age_hours > 2160 AND access_count = 0 AND importance < 0.3 {
                RETURN true;
            } ELSE {
                RETURN false;
            };
        };
        """,
        
        # Role-based access control (RBAC)
        "rbac_permissions": """
        -- Define roles
        DEFINE ROLE owner;
        DEFINE ROLE contributor;
        DEFINE ROLE viewer;
        DEFINE ROLE system;
        
        -- Grant permissions to roles
        -- Owner can do everything on their own data
        DEFINE ACCESS user_access ON DATABASE 
          FOR owner 
          FOR SELECT, CREATE, UPDATE, DELETE 
          WHERE user_id = $auth.user_id;
        
        -- Contributor can create and update but not delete
        DEFINE ACCESS user_access ON DATABASE 
          FOR contributor
          FOR SELECT, CREATE, UPDATE
          WHERE user_id = $auth.user_id;
        
        -- Viewer can only read
        DEFINE ACCESS user_access ON DATABASE 
          FOR viewer
          FOR SELECT
          WHERE user_id = $auth.user_id;
        
        -- System role has full access for internal processes
        DEFINE ACCESS system_access ON DATABASE 
          FOR system
          FOR SELECT, CREATE, UPDATE, DELETE;
        """,
    }
    
    def __init__(self, client):
        """Initialize schema manager.
        
        Args:
            client: SurrealDBClient instance
        """
        self.client = client
    
    async def create_schema(self) -> None:
        """Create the complete database schema."""
        logger.info("Creating KHALA database schema...")
        
        # Execute schema definitions in order
        creation_order = [
            "namespace",
            "database", 
            "memory_table",
            "memory_indexes",
            "entity_table",
            "relationship_table",
            "audit_log_table",
            "search_session_table",
            "skill_table",
            "functions",
            "rbac_permissions",
        ]
        
        for step in creation_order:
            if step in self.SCHEMA_DEFINITIONS:
                try:
                    await self._execute_schema_step(step)
                except Exception as e:
                    logger.error(f"Failed to create {step}: {e}")
                    raise
        
        logger.info("Database schema created successfully")
    
    async def drop_schema(self) -> None:
        """Drop all tables and indexes (for testing/reset)."""
        logger.warning("Dropping database schema...")
        
        drop_commands = [
            "REMOVE TABLE memory;",
            "REMOVE TABLE entity", 
            "REMOVE TABLE relationship",
            "REMOVE TABLE audit_log",
            "REMOVE TABLE search_session",
            "REMOVE TABLE skill",
            "REMOVE FUNCTION fn::decay_score",
            "REMOVE FUNCTION fn::should_promote",
            "REMOVE FUNCTION fn::should_archive",
        ]
        
        for command in drop_commands:
            try:
                async with self.client.get_connection() as conn:
                    await conn.query(command)
            except Exception as e:
                logger.debug(f"Error dropping schema component: {e}")
    
    async def verify_schema(self) -> Dict[str, bool]:
        """Verify that schema components exist and are working."""
        verification_results = {}
        
        # Test that tables exist
        table_checks = [
            ("memory", "SELECT count() FROM memory;"),
            ("entity", "SELECT count() FROM entity;"),
            ("relationship", "SELECT count() FROM relationship;"),
            ("audit_log", "SELECT count() FROM audit_log;"),
            ("search_session", "SELECT count() FROM search_session;"),
            ("skill", "SELECT count() FROM skill;"),
        ]
        
        for table_name, query in table_checks:
            try:
                async with self.client.get_connection() as conn:
                    await conn.query(query)
                    verification_results[f"table_{table_name}"] = True
            except Exception as e:
                logger.error(f"Table {table_name} verification failed: {e}")
                verification_results[f"table_{table_name}"] = False
        
        # Test that functions exist
        function_checks = [
            ("decay_score", "RETURN fn::decay_score(30.0, 0.8, 30.0);"),
            ("should_promote", "RETURN fn::should_promote('working', 1.0, 6, 0.9);"),
            ("should_archive", "RETURN fn::should_archive(2160.0, 0, 0.2);"),
        ]
        
        for func_name, query in function_checks:
            try:
                async with self.client.get_connection() as conn:
                    await conn.query(query)
                    verification_results[f"function_{func_name}"] = True
            except Exception as e:
                logger.error(f"Function {func_name} verification failed: {e}")
                verification_results[f"function_{func_name}"] = False
        
        return verification_results
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """Get information about the current schema."""
        schema_info = {}
        
        # Get table information
        table_info_query = """
        FOR table IN INFORMATION FOR TABLES {
            SELECT name, kind, count FROM table
        };
        """
        
        try:
            async with self.client.get_connection() as conn:
                result = await conn.query(table_info_query)
                schema_info["tables"] = result if result else []
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            schema_info["tables"] = []
        
        # Get index information
        index_info_query = """
        FOR index IN INFORMATION FOR INDEXES {
            SELECT name, table_name, index_type FROM index
        };
        """
        
        try:
            async with self.client.get_connection() as conn:
                result = await conn.query(index_info_query)
                schema_info["indexes"] = result if result else []
        except Exception as e:
            logger.error(f"Error getting index info: {e}")
            schema_info["indexes"] = []
        
        return schema_info
    
    async def _execute_schema_step(self, step_name: str) -> None:
        """Execute a single schema step with error handling."""
        schema_def = self.SCHEMA_DEFINITIONS[step_name]
        logger.info(f"Executing schema step: {step_name}")
        
        # Split multi-line definitions into individual statements
        statements = [stmt.strip() for stmt in schema_def.split(';') if stmt.strip()]
        
        async with self.client.get_connection() as conn:
            for statement in statements:
                try:
                    await conn.query(f"{statement};")
                except Exception as e:
                    # Some statements might fail if they already exist
                    if "already exists" in str(e).lower():
                        logger.debug(f"Statement already exists: {statement[:50]}...")
                    else:
                        logger.error(f"Error executing statement: {statement[:100]}... Error: {e}")
                        raise
        
        logger.info(f"Completed schema step: {step_name}")
