import unittest
import numpy as np
from khala.infrastructure.embeddings.quantization import VectorQuantizer

class TestVectorQuantizer(unittest.TestCase):

    def test_quantize_dequantize(self):
        original = [0.1, 0.5, -0.5, 0.9, -0.9, 0.0]
        quantized = VectorQuantizer.quantize_int8(original)
        reconstructed = VectorQuantizer.dequantize_int8(quantized)

        # Check lengths
        self.assertEqual(len(original), len(reconstructed))

        # Check values are close (within quantization error ~1/127 approx 0.0078)
        # We allow a slightly larger margin due to rounding
        np.testing.assert_allclose(original, reconstructed, atol=0.01)

    def test_bytes_roundtrip(self):
        original = [0.1, -0.2, 0.3]
        data = VectorQuantizer.compress_to_bytes(original)
        self.assertIsInstance(data, bytes)
        self.assertEqual(len(data), 3)

        reconstructed = VectorQuantizer.decompress_from_bytes(data)
        np.testing.assert_allclose(original, reconstructed, atol=0.01)

    def test_clipping(self):
        original = [1.5, -2.0] # Out of range
        quantized = VectorQuantizer.quantize_int8(original)

        # 1.5 -> 1.0 -> 127
        # -2.0 -> -1.0 -> -127
        self.assertEqual(quantized[0], 127)
        self.assertEqual(quantized[1], -127)

if __name__ == '__main__':
    unittest.main()
