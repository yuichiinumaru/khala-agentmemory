"""
Concept Cartography Service (Strategy 113).

Maps concepts (memories) to a 2D plane for "Nearness" visualization.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
import logging
from khala.domain.memory.entities import Memory

logger = logging.getLogger(__name__)

class ConceptCartographyService:
    """Service for projecting memory embeddings into 2D space."""

    def project_memories(self, memories: List[Memory]) -> Dict[str, Dict[str, float]]:
        """
        Project a list of memories into 2D space using PCA.

        Args:
            memories: List of Memory objects.

        Returns:
            Dictionary mapping memory ID to {'x': float, 'y': float}.
        """
        if not memories:
            return {}

        # Extract embeddings and IDs
        valid_memories = [m for m in memories if m.embedding is not None]
        if not valid_memories:
            logger.warning("No memories with embeddings found for projection.")
            return {}

        ids = [m.id for m in valid_memories]
        embeddings = np.array([m.embedding.to_numpy() for m in valid_memories])

        n_samples, n_features = embeddings.shape

        # If we have too few samples, we can't do meaningful PCA for 2D.
        # Handle edge cases:
        if n_samples == 1:
            return {ids[0]: {'x': 0.0, 'y': 0.0}}

        # If fewer features than 2, we can't project to 2D properly, but PCA handles it (components=1).
        n_components = min(2, n_samples, n_features)

        # Center the data
        mean = np.mean(embeddings, axis=0)
        centered_data = embeddings - mean

        try:
            # Compute SVD
            # U, S, Vt = np.linalg.svd(centered_data, full_matrices=False)
            # Principal components are V.T (columns of V)
            # Projected data is U * S
            # We want top 2 components.

            # Using SVD is standard for PCA implementation
            u, s, vt = np.linalg.svd(centered_data, full_matrices=False)

            # Project onto the first 2 principal components
            # If n_components < 2, we pad with 0.

            projected = u[:, :n_components] @ np.diag(s[:n_components])

            # Map back to IDs
            result = {}
            for i, memory_id in enumerate(ids):
                x = float(projected[i, 0]) if n_components >= 1 else 0.0
                y = float(projected[i, 1]) if n_components >= 2 else 0.0
                result[memory_id] = {'x': x, 'y': y}

            return result

        except Exception as e:
            logger.error(f"PCA projection failed: {e}")
            # Fallback: return zeros
            return {mid: {'x': 0.0, 'y': 0.0} for mid in ids}
