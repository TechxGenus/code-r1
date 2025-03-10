import rich
from rich.syntax import Syntax
from rich.rule import Rule
import time

from verl.utils.reward_score.coder1 import code_exec

def test_cpu_limit(note, code, stdin=None, expect_error=True):
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
        assert not succ, "Expecting a failure due to CPU time limit"
    else:
        assert succ, "Expecting a success"

# Test 1: Infinite loop
test_cpu_limit(
    "CPU limit: Infinite loop",
    """
# This should be terminated by the CPU time limit
while True:
    pass
"""
)

# Test 2: Busy loop with progress reporting
test_cpu_limit(
    "CPU limit: Busy loop with progress reporting",
    """
import time

start_time = time.time()
counter = 0

# Busy loop that reports progress
while True:
    counter += 1
    if counter % 1000000 == 0:
        elapsed = time.time() - start_time
        print(f"Iteration {counter}, elapsed time: {elapsed:.2f} seconds")
"""
)

# Test 3: A test that should pass (completes within CPU time limit)
test_cpu_limit(
    "CPU limit: Quick calculation (should pass)",
    """
# Calculate factorial of a reasonable number
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

result = factorial(100)
print(f"Factorial of 100: {result}")
""",
    expect_error=False
)

print("All CPU limit tests completed!") 