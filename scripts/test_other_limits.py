import rich
from rich.syntax import Syntax
from rich.rule import Rule
import time

from verl.utils.reward_score.coder1 import code_exec

def test_limit(note, code, stdin=None, expect_error=True, error_msg=None):
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
        assert not succ, "Expecting a failure due to resource limit"
    else:
        assert succ, "Expecting a success"

# Test 1: File size limit (try to create a file larger than 10MB)
test_limit(
    "File size limit: Create large file (>10MB)",
    """
import os

# Try to create a 20MB file
file_path = "large_file.bin"
with open(file_path, "wb") as f:
    # Write 20MB of data (20 * 1024 * 1024 bytes)
    f.write(b'0' * (20 * 1024 * 1024))

# Check the file size
size_mb = os.path.getsize(file_path) / (1024 * 1024)
print(f"Successfully created file of size: {size_mb:.2f} MB")
""",
    error_msg=["file too large", "file size limit", "resource"]
)

# Test 2: Process limit (try to create more than 32 processes)
test_limit(
    "Process limit: Create many processes",
    """
import multiprocessing
import time

def worker():
    # Just sleep for a bit
    time.sleep(1)
    return "Done"

if __name__ == "__main__":
    processes = []
    # Try to create 50 processes (more than the 32 limit)
    for i in range(50):
        p = multiprocessing.Process(target=worker)
        processes.append(p)
        p.start()
        print(f"Started process {i+1}")
    
    # Wait for all processes to complete
    for p in processes:
        p.join()
    
    print("All processes completed successfully")
""",
    error_msg=["resource", "process", "limit"]
)

# Test 3: Small file creation (should pass)
test_limit(
    "File size limit: Create small file (should pass)",
    """
import os

# Create a 1MB file (should be within limits)
file_path = "small_file.bin"
try:
    with open(file_path, "wb") as f:
        # Write 1MB of data
        f.write(b'0' * (1 * 1024 * 1024))
    
    # Check the file size
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"Successfully created file of size: {size_mb:.2f} MB")
except Exception as e:
    print(f"Error creating file: {str(e)}")
finally:
    # Clean up
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except:
        pass
""",
    expect_error=False
)

# Test 4: Few processes (should pass)
test_limit(
    "Process limit: Create few processes (should pass)",
    """
import multiprocessing
import time

def worker(num):
    # Just sleep for a bit
    time.sleep(0.1)
    return f"Worker {num} done"

if __name__ == "__main__":
    processes = []
    try:
        # Create 5 processes (within the 32 limit)
        for i in range(5):
            p = multiprocessing.Process(target=worker, args=(i,))
            processes.append(p)
            p.start()
            print(f"Started process {i+1}")
        
        # Wait for all processes to complete
        for p in processes:
            p.join()
        
        print("All processes completed successfully")
    except Exception as e:
        print(f"Error: {str(e)}")
""",
    expect_error=False
)

print("All other limit tests completed!") 