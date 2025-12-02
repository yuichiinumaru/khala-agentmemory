# Spatial Memory Implementation - WIP Report

**Date:** 2025-12-02
**Status:** In Progress (Blocked on Strategy 113)

## Overview
This report summarizes the implementation progress of **Module 11.C.1 Geospatial (Strategies 111-115)**.

## Implemented Features

### 1. Domain Models
-   **Location Value Object**: Implemented `khala.domain.memory.value_objects.Location` with `latitude`, `longitude`, `address`, etc. Supports validation and GeoJSON conversion.
-   **Memory Entity**: Updated `Memory` entity to include optional `location` field.

### 2. Infrastructure (SurrealDB)
-   **Schema**: Updated `memory` table to use `DEFINE FIELD location ON memory TYPE option<geometry<point>>;`.
-   **Client**: Updated `SurrealDBClient` to:
    -   Serialize `Memory.location` to `surrealdb.GeometryPoint` for persistence.
    -   Deserialize `GeometryPoint` back to `Location` domain object.
    -   Import `GeometryPoint` from `surrealdb.data.types.geometry` (SurrealDB Python SDK specific path).

### 3. Services
-   **SpatialMemoryService**: Created `khala/application/services/spatial_memory_service.py` implementing:
    -   `update_memory_location` (Strategy 111): Updates location field atomically.
    -   `find_nearby_memories` (Strategy 112): Uses `geo::distance` with explicit casting `<point>[$lon, $lat]`. **Verified Working**.
    -   `get_memory_trajectory` (Strategy 114): Retrieves location history.
    -   `find_spatial_clusters` (Strategy 115): Uses `geo::hash::encode`.

## Current Blocker: Region Queries (Strategy 113)

The method `find_within_region(polygon_coords)` is currently failing tests.

### The Issue
The query relies on `location INSIDE $polygon`. We need to pass a Polygon geometry as `$polygon`.

1.  **SDK Limitation**: The `surrealdb` Python SDK's `GeometryPolygon` class constructor signature appears to be `(line1, line2, *other_lines)`. This enforces a minimum of **two linear rings** (e.g., an exterior and a hole). Standard simple polygons have only **one** linear ring (the exterior). Passing a single `GeometryLine` raises `TypeError`.
2.  **Binding Limitation**: Passing a raw Python dictionary `{'type': 'Polygon', ...}` as the parameter fails with validation errors from SurrealDB (even when casting with `<geometry>$polygon`), likely due to strict type matching or serialization behavior in the client.

### Proposed Solution
To resolve this, we plan to refactor `find_within_region` to **construct the Polygon geometry directly within the SurrealQL query string**, rather than relying on parameter binding for the geometry object. This bypasses the SDK's constructor limitations.

```sql
SELECT * FROM memory
WHERE location IS NOT NONE
AND location INSIDE {
    type: 'Polygon',
    coordinates: [[ [lon1, lat1], [lon2, lat2], ... ]]
};
```

## Next Steps
1.  Refactor `find_within_region` to use string formatting for the polygon coordinates.
2.  Verify the fix with `tests/integration/test_spatial_memory.py`.
3.  Finalize the task.
