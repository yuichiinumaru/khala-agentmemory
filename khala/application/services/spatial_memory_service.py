"""Spatial Memory Service.

This service implements Strategies 111-115 (Geospatial Optimization) by providing
functionality for spatial memory organization, proximity search, and trajectory tracking.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from datetime import datetime

from khala.domain.memory.value_objects import Location
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)


class SpatialMemoryService:
    """Service for managing spatial aspects of memory."""

    def __init__(self, db_client: SurrealDBClient):
        """Initialize the spatial memory service.

        Args:
            db_client: SurrealDB client for database operations.
        """
        self.db_client = db_client

    async def update_memory_location(
        self,
        memory_id: str,
        latitude: float,
        longitude: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update the location of a specific memory (Strategy 111).

        Args:
            memory_id: ID of the memory to update.
            latitude: Latitude coordinate.
            longitude: Longitude coordinate.
            metadata: Optional additional metadata for the location.

        Returns:
            True if successful, False otherwise.
        """
        # Fetch memory first
        memory = await self.db_client.get_memory(memory_id)
        if not memory:
            logger.error(f"Memory {memory_id} not found")
            return False

        # Strategy 114: Track history in versions
        if memory.location:
            # Create a snapshot of the current state before update
            snapshot = {
                "updated_at": datetime.now().isoformat(),
                "location": memory.location.to_geojson(),
                "change_type": "location_update"
            }
            memory.versions.append(snapshot)

        # Update location
        memory.location = Location(
            latitude=latitude,
            longitude=longitude,
            metadata=metadata or {}
        )

        try:
            # Use client's update_memory to persist
            await self.db_client.update_memory(memory)
            return True
        except Exception as e:
            logger.error(f"Failed to update location for memory {memory_id}: {e}")
            return False

    async def find_nearby_memories(
        self,
        latitude: float,
        longitude: float,
        max_distance_km: float = 10.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Find memories near a specific location (Strategy 112).

        Args:
            latitude: Center latitude.
            longitude: Center longitude.
            max_distance_km: Maximum distance in kilometers (default 10km).
            limit: Maximum number of results.

        Returns:
            List of memory records with distance information.
        """
        # SurrealDB uses meters for distance
        max_distance_meters = max_distance_km * 1000

        query = """
        SELECT *,
               geo::distance(location, <point>[$lon, $lat]) as distance
        FROM memory
        WHERE location IS NOT NONE
          AND geo::distance(location, <point>[$lon, $lat]) < $dist
        ORDER BY distance ASC
        LIMIT $limit;
        """

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(
                    query,
                    {
                        "lat": latitude,
                        "lon": longitude,
                        "dist": max_distance_meters,
                        "limit": limit
                    }
                )

                # Handle case where result is an error string
                if isinstance(result, str):
                    logger.error(f"Query returned error string: {result}")
                    return []

                if result and isinstance(result, list):
                    # Check if the first item is a result dict or list of records
                    if len(result) > 0:
                        first = result[0]
                        # Check if it looks like a QueryResponse wrapper
                        if isinstance(first, dict) and 'status' in first and 'result' in first:
                            return first['result']
                        # Otherwise assume it is the list of records itself
                        return result

                # Handle SurrealDB response format
                if isinstance(result, list) and len(result) > 0:
                    first = result[0]
                    if isinstance(first, dict) and 'status' in first and 'result' in first:
                        return first['result']
                    return result
                return []
        except Exception as e:
            logger.error(f"Failed to find nearby memories: {e}")
            return []

    async def find_within_region(
        self,
        polygon_coords: List[Tuple[float, float]]
    ) -> List[Dict[str, Any]]:
        """Find memories within a polygonal region (Strategy 113).

        Args:
            polygon_coords: List of (lon, lat) tuples defining the polygon vertices.
                           The first and last points must match to close the polygon.

        Returns:
            List of memories inside the region.
        """
        # Ensure polygon is closed
        if not polygon_coords:
            return []

        if polygon_coords[0] != polygon_coords[-1]:
            polygon_coords.append(polygon_coords[0])

        # Construct Polygon as dict to avoid SDK constructor issues with single-ring polygons
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[
                [lon, lat] for lon, lat in polygon_coords
            ]]
        }

        query = """
        SELECT * FROM memory
        WHERE location IS NOT NONE
          AND location INSIDE <geometry>$polygon;
        coords_list = [[lon, lat] for lon, lat in polygon_coords]

        # Construct GeoJSON Polygon structure
        # Note: GeoJSON coordinates for Polygon are [ [ [x,y], ... ] ] (array of rings)
        polygon_struct = {
            "type": "Polygon",
            "coordinates": [coords_list]
        }

        # Serialize to JSON string to inject directly
        # This bypasses potential SDK binding issues with complex geometry types
        polygon_json = json.dumps(polygon_struct)

        query = f"""
        SELECT * FROM memory
        WHERE location IS NOT NONE
          AND location INSIDE {polygon_json};
        """

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query)
                result = await conn.query(
                    query,
                    {"polygon": polygon_data}
                )

                if isinstance(result, list) and len(result) > 0:
                    first = result[0]
                    if isinstance(first, dict) and 'status' in first and 'result' in first:
                        return first['result']
                    return result
                return []
        except Exception as e:
            logger.error(f"Failed to find memories in region: {e}")
            return []

    async def get_memory_trajectory(self, memory_id: str) -> List[Dict[str, Any]]:
        """Track movement/location changes of a memory over time (Strategy 114).

        This relies on the 'versions' array which stores history.

        Args:
            memory_id: ID of the memory.

        Returns:
            List of historical locations with timestamps.
        """
        # Normalize ID
        if "memory:" in memory_id:
            memory_id = memory_id.split("memory:")[1]

        query = """
        SELECT id, updated_at, location, versions
        FROM memory
        WHERE id = type::thing('memory', $id);
        """

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"id": memory_id})

                # Check for QueryResponse wrapper
                records = []
                if isinstance(result, list) and len(result) > 0:
                    first = result[0]
                    if isinstance(first, dict) and 'status' in first and 'result' in first:
                        records = first['result']
                    else:
                        records = result
                else:
                    return []

                if not records:
                    return []

                memory = records[0]
                trajectory = []

                # Helper to normalize timestamp
                def to_iso(ts):
                    if isinstance(ts, datetime):
                        return ts.isoformat()
                    return str(ts) if ts else ""

                # Add current location
                if memory.get('location'):
                    trajectory.append({
                        "timestamp": to_iso(memory.get('updated_at')),
                        "location": memory.get('location'),
                        "source": "current"
                    })

                # Check versions for past locations
                versions = memory.get('versions') or []
                for ver in versions:
                    if ver.get('location'):
                        trajectory.append({
                            "timestamp": to_iso(ver.get('updated_at') or ver.get('created_at')),
                            "location": ver.get('location'),
                            "source": "history"
                        })

                # Sort by timestamp (descending)
                trajectory.sort(key=lambda x: x.get('timestamp') or "", reverse=True)
                return trajectory

        except Exception as e:
            logger.error(f"Failed to get trajectory for memory {memory_id}: {e}")
            return []

    async def find_spatial_clusters(
        self,
        grid_precision: int = 6
    ) -> List[Dict[str, Any]]:
        """Find clusters of memories based on location (Strategy 115).

        Uses geohash for efficient clustering.

        Args:
            grid_precision: Precision of geohash (higher = smaller cells).

        Returns:
            List of clusters with count and center point.
        """
        query = """
        SELECT count() as count,
               geo::hash::encode(location, $prec) as geohash,
               math::mean(location.coordinates[0]) as center_lon,
               math::mean(location.coordinates[1]) as center_lat
        FROM memory
        WHERE location IS NOT NONE
        GROUP BY geohash
        ORDER BY count DESC;
        """

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"prec": grid_precision})

                if isinstance(result, list) and len(result) > 0:
                    first = result[0]
                    if isinstance(first, dict) and 'status' in first and 'result' in first:
                        return first['result']
                    return result
                return []
        except Exception as e:
            logger.error(f"Failed to find spatial clusters: {e}")
            return []
