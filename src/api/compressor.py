# -*- coding: utf-8 -*-
"""
Compressor module - provides gzip compression/decompression for JSON-RPC responses.
Compatible with Jython 2.7 (Java 7/8) using zlib module.
"""
import struct

# Try to import zlib (works in both Jython and CPython)
try:
    import zlib
    ZLIB_AVAILABLE = True
except ImportError:
    ZLIB_AVAILABLE = False

# For CPython server.py fallback
if not ZLIB_AVAILABLE:
    import gzip


def _gzip_compress(data, compresslevel=6):
    """
    GZIP compression using zlib (compatible with both Jython 2.7 and CPython).
    This produces standard GZIP format data with proper header and trailer.
    """
    if not ZLIB_AVAILABLE:
        raise RuntimeError("zlib module not available")

    # GZIP header (RFC 1952)
    header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff'

    # Compress using zlib with negative window bits for raw deflate
    compressor = zlib.compressobj(compresslevel, zlib.DEFLATED, -zlib.MAX_WBITS)
    compressed = compressor.compress(data)
    compressed += compressor.flush()

    # GZIP trailer (CRC32 and original size mod 2^32)
    crc = zlib.crc32(data) & 0xffffffff
    trailer = struct.pack('<II', crc, len(data) & 0xffffffff)

    return header + compressed + trailer


def _gzip_decompress(data):
    """
    GZIP decompression using zlib (compatible with both Jython 2.7 and CPython).
    """
    if not ZLIB_AVAILABLE:
        raise RuntimeError("zlib module not available")

    # Verify GZIP header
    if len(data) < 10 or (data[0:2] != b'\x1f\x8b' if isinstance(data[0:2], bytes) else ord(data[0]) != 0x1f or ord(data[1]) != 0x8b):
        raise ValueError("Not a gzip file")

    # Skip GZIP header (minimum 10 bytes)
    flags = ord(data[3]) if isinstance(data[3], int) else ord(data[3])
    offset = 10

    if flags & 0x04:  # FEXTRA
        xlen = ord(data[offset]) if isinstance(data[offset], int) else ord(data[offset])
        xlen += (ord(data[offset+1]) if isinstance(data[offset+1], int) else ord(data[offset+1])) << 8
        offset += 2 + xlen
    if flags & 0x08:  # FNAME
        while offset < len(data) and data[offset] != b'\x00' and data[offset] != 0:
            offset += 1
        offset += 1
    if flags & 0x10:  # FCOMMENT
        while offset < len(data) and data[offset] != b'\x00' and data[offset] != 0:
            offset += 1
        offset += 1
    if flags & 0x02:  # FHCRC
        offset += 2

    # Decompress using zlib with negative window bits
    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    decompressed = decompressor.decompress(data[offset:-8])
    decompressed += decompressor.flush()

    return decompressed


class Compressor:
    """GZIP compression utility compatible with Jython and CPython"""

    MIN_COMPRESS_SIZE = 256

    @classmethod
    def compress(cls, data):
        """Compress byte data using GZIP."""
        if not isinstance(data, (str, bytes)):
            data = str(data)

        if ZLIB_AVAILABLE:
            return cls._compress_zlib(data)
        else:
            return cls._compress_gzip(data)

    @classmethod
    def decompress(cls, compressed_data):
        """Decompress GZIP compressed byte data."""
        if ZLIB_AVAILABLE:
            return cls._decompress_zlib(compressed_data)
        else:
            return cls._decompress_gzip(compressed_data)

    @classmethod
    def _compress_zlib(cls, data):
        """GZIP compression using zlib (works in both Jython and CPython)"""
        return _gzip_compress(data, compresslevel=6)

    @classmethod
    def _decompress_zlib(cls, compressed_data):
        """GZIP decompression using zlib (works in both Jython and CPython)"""
        return _gzip_decompress(compressed_data)

    @classmethod
    def _compress_gzip(cls, data):
        """Python gzip module fallback (CPython only)"""
        import io
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb') as f:
            f.write(data)
        return buf.getvalue()

    @classmethod
    def _decompress_gzip(cls, compressed_data):
        """Python gzip module fallback (CPython only)"""
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(compressed_data), mode='rb') as f:
            return f.read()

    @classmethod
    def should_compress(cls, size):
        """Check if data should be compressed based on size"""
        return size >= cls.MIN_COMPRESS_SIZE
