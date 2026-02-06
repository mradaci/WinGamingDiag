"""
WinGamingDiag - Performance Benchmark
Simple performance benchmarking module
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import time
import math


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


class PerformanceBenchmark:
    """
    Simple performance benchmarking suite.
    Tests CPU, memory, and basic operations performance.
    """
    
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


__all__ = ['PerformanceBenchmark', 'BenchmarkResult', 'BenchmarkSuite']