import rich
from rich.syntax import Syntax
from rich.rule import Rule
import time

from verl.utils.reward_score.coder1 import code_exec

def test_file_limit(note, code, stdin=None, expect_error=True):
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
        assert not succ, "Expecting a failure due to file limit"
        assert "Too many open files" in output or "Resource temporarily unavailable" in output, "Expected file limit error"
    else:
        assert succ, "Expecting a success"

# Test 1: Try to open more than 10 file handles simultaneously
test_file_limit(
    "File limit: Open more than 10 file handles simultaneously",
    """
import tempfile

# Try to open 15 file handles simultaneously
file_handles = []
for i in range(15):
    temp_file = tempfile.NamedTemporaryFile()
    file_handles.append(temp_file)
    print(f"Opened file handle {i+1}")
print("Successfully opened all file handles")
"""
)

# Test 2: A test that should pass (creates fewer than 10 files)
test_file_limit(
    "File limit: Create fewer than 10 files (should pass)",
    """
import tempfile

# Create 5 files (should be within limits)
file_handles = []
for i in range(5):
    temp_file = tempfile.NamedTemporaryFile()
    file_handles.append(temp_file)
    print(f"Opened file handle {i+1}")

print("Successfully opened all file handles")

# Close all file handles
for handle in file_handles:
    handle.close()
""",
    expect_error=False
)

print("All file limit tests completed!") 