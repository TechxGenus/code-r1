import rich
from rich.syntax import Syntax
from rich.rule import Rule
import time

from verl.utils.reward_score.coder1 import code_exec

def test_memory_limit(note, code, stdin=None, expect_error=True):
    rich.print(Rule(note))
    rich.print(Syntax(code, "python", word_wrap=True))
    start_time = time.time()
    succ, output = code_exec(code, stdin=stdin)
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"{succ = }")
    print(f"Execution time: {execution_time:.2f} seconds")
    
    if not succ:
        print(f"Error:\n{output}")
    else:
        print(f"Output:\n{output}")
    
    if expect_error:
        assert not succ, "Expecting a failure due to memory limit"
        assert "MemoryError" in output or "Resource temporarily unavailable" in output, "Expected memory error"
    else:
        assert succ, "Expecting a success"

# Test 1: Allocate a large array (more than 2GB)
test_memory_limit(
    "Memory limit: Allocate large array (>2GB)",
    """
import numpy as np
# Try to allocate a 3GB array (3 * 10^9 * 8 bytes = 24GB)
large_array = np.ones((3 * 10**9,), dtype=np.float64)
print(f"Array shape: {large_array.shape}, Size: {large_array.nbytes / (1024**3):.2f} GB")
"""
)

# Test 2: Gradually increasing memory usage
test_memory_limit(
    "Memory limit: Gradually increasing memory usage",
    """
import numpy as np
arrays = []
chunk_size = 100 * 1024 * 1024  # 100MB chunks
# Try to allocate up to 3GB in 100MB chunks
for i in range(30):
    arrays.append(np.ones((chunk_size,), dtype=np.uint8))
    total_allocated = sum(arr.nbytes for arr in arrays)
    print(f"Allocated {total_allocated / (1024**3):.2f} GB")
print("Successfully allocated all memory")
"""
)

# Test 3: Memory leak simulation
test_memory_limit(
    "Memory limit: Memory leak simulation",
    """
import numpy as np

def leak_memory():
    leaked = []
    for i in range(1000):
        # Each iteration adds about 10MB
        leaked.append(np.random.random((10**6,)))
        if i % 10 == 0:
            print(f"Iteration {i}: Allocated approximately {(i+1) * 10} MB")
    return leaked

# This should eventually hit the memory limit
result = leak_memory()
print("Completed without memory errors")
"""
)

# Test 4: A test that should pass (uses less than 2GB)
test_memory_limit(
    "Memory limit: Small array (should pass)",
    """
import numpy as np
# Allocate a 1GB array
array = np.ones((125 * 10**6,), dtype=np.float64)  # ~1GB
print(f"Array shape: {array.shape}, Size: {array.nbytes / (1024**3):.2f} GB")
""",
    expect_error=False
)

print("All memory limit tests completed!") 