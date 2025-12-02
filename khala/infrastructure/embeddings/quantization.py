import numpy as np
from typing import List

class VectorQuantizer:
    """Utility for vector quantization."""

    @staticmethod
    def quantize_int8(vector: List[float]) -> List[int]:
        """Quantize a float vector to int8 (-128 to 127).

        Assumes normalized vectors (values roughly between -1 and 1).
        Values outside [-1, 1] are clipped.
        """
        arr = np.array(vector, dtype=np.float32)

        # Clip to [-1, 1]
        arr = np.clip(arr, -1.0, 1.0)

        # Scale to [-127, 127] and round
        quantized = np.round(arr * 127).astype(np.int8)

        return quantized.tolist()

    @staticmethod
    def dequantize_int8(vector: List[int]) -> List[float]:
        """Dequantize an int8 vector back to float."""
        arr = np.array(vector, dtype=np.int8)

        # Scale back
        dequantized = (arr.astype(np.float32) / 127.0)

        return dequantized.tolist()

    @staticmethod
    def compress_to_bytes(vector: List[float]) -> bytes:
        """Quantize and pack to bytes."""
        quantized = VectorQuantizer.quantize_int8(vector)
        return np.array(quantized, dtype=np.int8).tobytes()

    @staticmethod
    def decompress_from_bytes(data: bytes) -> List[float]:
        """Unpack bytes and dequantize."""
        arr = np.frombuffer(data, dtype=np.int8)
        return VectorQuantizer.dequantize_int8(arr.tolist())
