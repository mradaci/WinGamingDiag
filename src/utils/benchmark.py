"""
WinGamingDiag - Performance Benchmark
Simple performance benchmarking module with disk I/O testing
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import time
import math
import os
import tempfile
import random
from enum import Enum


@dataclass
class BenchmarkResult:
    """Result of a benchmark test"""
    name: str
    score: float
    unit: str
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results"""
    timestamp: datetime
    total_duration_ms: float
    results: List[BenchmarkResult] = field(default_factory=list)
    
    @property
    def overall_score(self) -> float:
        """Calculate overall performance score"""
        if not self.results:
            return 0.0
        
        # Weight different benchmarks
        weights = {
            'cpu': 0.3,
            'memory': 0.2,
            'math': 0.2,
            'string': 0.15,
            'disk': 0.15
        }
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for result in self.results:
            weight = weights.get(result.name.lower().split()[0], 0.1)
            # Normalize score to 0-100 scale
            normalized_score = min(100, max(0, result.score / 1000 * 100))
            total_weighted_score += normalized_score * weight
            total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0.0


class BenchmarkSize(Enum):
    """Configurable benchmark sizes for disk I/O testing"""
    QUICK = 32      # 32MB - Fast test
    DEFAULT = 128   # 128MB - Standard test
    THOROUGH = 512  # 512MB - Comprehensive test


class PerformanceBenchmark:
    """
    Simple performance benchmarking suite.
    Tests CPU, memory, basic operations, and disk I/O performance.
    """
    
    def __init__(self, disk_test_size: BenchmarkSize = BenchmarkSize.DEFAULT):
        """
        Initialize benchmark with configurable disk test size
        
        Args:
            disk_test_size: Size of disk benchmark (QUICK=32MB, DEFAULT=128MB, THOROUGH=512MB)
        """
        self.disk_test_size = disk_test_size
    
    def run_benchmarks(self) -> BenchmarkSuite:
        """
        Run complete benchmark suite
        
        Returns:
            BenchmarkSuite with all results
        """
        start_time = time.time()
        results = []
        
        # CPU benchmark
        results.append(self._benchmark_cpu())
        
        # Memory benchmark
        results.append(self._benchmark_memory())
        
        # Math operations benchmark
        results.append(self._benchmark_math())
        
        # String operations benchmark
        results.append(self._benchmark_string())
        
        # Disk I/O benchmark
        results.append(self._benchmark_disk_io())
        
        total_duration = (time.time() - start_time) * 1000
        
        return BenchmarkSuite(
            timestamp=datetime.now(),
            total_duration_ms=total_duration,
            results=results
        )
    
    def _benchmark_cpu(self) -> BenchmarkResult:
        """Benchmark CPU performance"""
        start = time.time()
        
        # CPU-intensive calculation: prime number check
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(math.sqrt(n)) + 1):
                if n % i == 0:
                    return False
            return True
        
        primes_found = 0
        for num in range(2, 50000):
            if is_prime(num):
                primes_found += 1
        
        duration = (time.time() - start) * 1000
        
        # Score: higher is better (operations per ms)
        score = primes_found / max(duration, 1) * 1000
        
        return BenchmarkResult(
            name="CPU Prime Calculation",
            score=score,
            unit="ops/ms",
            duration_ms=duration,
            details={'primes_found': primes_found}
        )
    
    def _benchmark_memory(self) -> BenchmarkResult:
        """Benchmark memory performance"""
        start = time.time()
        
        # Memory allocation and manipulation
        size = 1000000
        data = [i for i in range(size)]
        
        # Various memory operations
        total = sum(data)
        data.reverse()
        data.sort()
        
        duration = (time.time() - start) * 1000
        
        # Score: operations per ms
        score = size / max(duration, 1)
        
        return BenchmarkResult(
            name="Memory Operations",
            score=score,
            unit="ops/ms",
            duration_ms=duration,
            details={'elements_processed': size}
        )
    
    def _benchmark_math(self) -> BenchmarkResult:
        """Benchmark mathematical operations"""
        start = time.time()
        
        iterations = 1000000
        result = 0.0
        
        for i in range(iterations):
            result += math.sin(i * 0.01) * math.cos(i * 0.01)
        
        duration = (time.time() - start) * 1000
        
        # Score: operations per ms
        score = iterations / max(duration, 1)
        
        return BenchmarkResult(
            name="Math Operations",
            score=score,
            unit="ops/ms",
            duration_ms=duration,
            details={'iterations': iterations, 'result': result}
        )
    
    def _benchmark_string(self) -> BenchmarkResult:
        """Benchmark string operations"""
        start = time.time()
        
        iterations = 100000
        strings = []
        
        for i in range(iterations):
            s = f"String test {i} with some data"
            strings.append(s.upper())
            strings.append(s.lower())
            strings.append(s.replace("test", "benchmark"))
        
        duration = (time.time() - start) * 1000
        
        # Score: operations per ms
        score = (iterations * 3) / max(duration, 1)
        
        return BenchmarkResult(
            name="String Operations",
            score=score,
            unit="ops/ms",
            duration_ms=duration,
            details={'strings_processed': len(strings)}
        )
    
    def _benchmark_disk_io(self) -> BenchmarkResult:
        """Benchmark disk sequential read/write performance"""
        # Use configurable test size
        file_size_mb = self.disk_test_size.value
        chunk_size = 1024 * 1024  # 1MB chunks
        
        # Create temp file with random name
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"wingamingdiag_bench_{random.randint(1000, 9999)}.tmp")
        
        # Generate random data (defeats compression)
        data = os.urandom(chunk_size)
        
        try:
            # Write Test
            start_write = time.time()
            with open(temp_file, 'wb') as f:
                for _ in range(file_size_mb):
                    f.write(data)
                # Force write to disk
                f.flush()
                os.fsync(f.fileno())
            end_write = time.time()
            
            write_time = end_write - start_write
            write_speed_mbps = file_size_mb / max(write_time, 0.001)
            
            # Read Test
            start_read = time.time()
            with open(temp_file, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
            end_read = time.time()
            
            read_time = end_read - start_read
            read_speed_mbps = file_size_mb / max(read_time, 0.001)
            
            # Clean up
            os.remove(temp_file)
            
            # Score: Combined MB/s scaled for overall scoring
            combined_speed = (write_speed_mbps + read_speed_mbps) / 2
            score = combined_speed * 10  # Scale to match other benchmark scores
            
            return BenchmarkResult(
                name="Disk I/O (Seq)",
                score=score,
                unit="MB/s",
                duration_ms=(write_time + read_time) * 1000,
                details={
                    'write_speed_mbps': round(write_speed_mbps, 2),
                    'read_speed_mbps': round(read_speed_mbps, 2),
                    'file_size_mb': file_size_mb,
                    'test_size_label': self.disk_test_size.name
                }
            )
            
        except Exception as e:
            # Cleanup if failed
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            return BenchmarkResult(
                name="Disk I/O (Seq)",
                score=0,
                unit="MB/s",
                duration_ms=0,
                details={'error': str(e)}
            )


__all__ = ['PerformanceBenchmark', 'BenchmarkResult', 'BenchmarkSuite', 'BenchmarkSize']