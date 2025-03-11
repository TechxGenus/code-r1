import os
import subprocess
import resource
import signal
import tempfile

from tempfile import NamedTemporaryFile, TemporaryDirectory

from .utils import _ERROR_MSG_PREFIX, _DEFAULT_TIMEOUT_SECONDS

# So I tried 4 approaches for code execution (after a few all-nighters...):
# 1. _remote_code_exec_ces -- Directly using https://github.com/cassanof/code_exec_server
#       - Is fast but leads to unreasonable false positives of timeouts
#       - I tried to alleviate this by (i) restarting the server frequently; (ii) bigger timeout; (iii) lower concurrency
#       - Still feels 10% false positives and bad concurrency
# 2. _remote_code_exec_kira -- Extending https://github.com/cassanof/code_exec_server to support my format and use some OS features for isolation
#       - Less unreasonable timeouts but the concurrency is very bad, stucking at create temp dirs all the time
# 3. https://e2b.dev/
#       - Concurrency is fine
#       - Does not support STDIN by default - needs some hack to support it
#       - I don't want to pay other servers when I have 192 physical CPUs...
# 4. _code_exec_firejail -- Using firejail (https://github.com/netblue30/firejail)
#       - User space isolation (some ulimit/rlimit features)
#       - Drop-in OS isolation via seccomp (blocking socket, etc.)
#       - Concurrency is the best so far
#       - This is not the safest - but docker is not safe either :L. Looks good enough for my dataset anyways.
# 5. Direct execution (unsafe mode) -- No sandbox, directly runs Python code
#       - No isolation, potentially unsafe
#       - Best performance and concurrency
#       - Use only in trusted environments with trusted code
#       - Added basic resource limitations using Python's resource module

CLI_ARG_SIZE_LIMIT = 1024 * 3

# Resource limits
MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024  # 2GB
MAX_OPEN_FILES = 10
MAX_PROCESSES = 32
CPU_TIME_LIMIT = 30  # seconds
FILE_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB

# Wrapper script to set resource limits before executing user code
RESOURCE_LIMIT_WRAPPER = """
import resource
import sys
import os

def set_resource_limits():
    # Memory limit (2GB)
    resource.setrlimit(resource.RLIMIT_AS, ({memory_limit}, {memory_limit}))
    
    # File size limit (10MB)
    resource.setrlimit(resource.RLIMIT_FSIZE, ({file_size_limit}, {file_size_limit}))
    
    # Process limit (32)
    resource.setrlimit(resource.RLIMIT_NPROC, ({max_processes}, {max_processes}))
    
    # Open files limit (10)
    resource.setrlimit(resource.RLIMIT_NOFILE, ({max_open_files}, {max_open_files}))
    
    # CPU time limit
    resource.setrlimit(resource.RLIMIT_CPU, ({cpu_time_limit}, {cpu_time_limit}))

# Set resource limits
set_resource_limits()

# Execute the actual user code
{user_code_execution}
"""


def code_exec_firejail(code, stdin: str = None, timeout=_DEFAULT_TIMEOUT_SECONDS, pytest: str = None):
    # Instead of copying all environment variables, only copy common ones
    env = {}
    # Common environment variables that might be needed
    common_env_vars = [
        # Basic system and user environment
        "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
        "SHELL", "TMPDIR", "TZ",
        
        # Python related
        "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONOPTIMIZE", 
        "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "PYTHONIOENCODING",
        
        # Numerical and scientific libraries
        "NUMPY_EXPERIMENTAL_ARRAY_FUNCTION", "NPY_NUM_BUILD_JOBS",
        "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMEXPR_NUM_THREADS",
        
        # GPU related
        "CUDA_VISIBLE_DEVICES", "CUDA_DEVICE_ORDER", "PYTORCH_CUDA_ALLOC_CONF",
        
        # Proxy and network settings
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
        
        # Other potentially useful variables
        "LD_LIBRARY_PATH", "DISPLAY", "MALLOC_TRIM_THRESHOLD_"
    ]
    
    # Copy only common environment variables if they exist
    for var in common_env_vars:
        if var in os.environ:
            env[var] = os.environ[var]
    
    # Add specific environment variables needed for execution
    env["OPENBLAS_NUM_THREADS"] = "1"
    
    # Set temporary directory to limit file creation
    temp_dir = tempfile.mkdtemp(prefix="code_exec_")
    env["TMPDIR"] = temp_dir
    
    try:
        if pytest:
            # solution is in {tmpdir}/solution.py
            with TemporaryDirectory() as tmpdir:
                assert stdin is None, "STDIN is not supported with pytest"
                # Write the solution to a file
                with open(os.path.join(tmpdir, "solution.py"), "w") as f:
                    f.write(code)
                with open(os.path.join(tmpdir, "test_solution.py"), "w") as f:
                    f.write(pytest)
                
                # Create a wrapper script that sets resource limits
                wrapper_code = RESOURCE_LIMIT_WRAPPER.format(
                    memory_limit=MEMORY_LIMIT_BYTES,
                    file_size_limit=FILE_SIZE_LIMIT,
                    max_processes=MAX_PROCESSES,
                    max_open_files=MAX_OPEN_FILES,
                    cpu_time_limit=CPU_TIME_LIMIT,
                    user_code_execution=f"import pytest\nsys.exit(pytest.main(['{tmpdir}']))"
                )
                
                wrapper_path = os.path.join(tmpdir, "wrapper.py")
                with open(wrapper_path, "w") as f:
                    f.write(wrapper_code)
                
                command = ["python3", wrapper_path]
                result = subprocess.run(
                    command,
                    cwd=tmpdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=False,
                    timeout=timeout
                )
        else:
            if len(code) < CLI_ARG_SIZE_LIMIT:
                # For inline code, wrap it with resource limits
                wrapped_code = RESOURCE_LIMIT_WRAPPER.format(
                    memory_limit=MEMORY_LIMIT_BYTES,
                    file_size_limit=FILE_SIZE_LIMIT,
                    max_processes=MAX_PROCESSES,
                    max_open_files=MAX_OPEN_FILES,
                    cpu_time_limit=CPU_TIME_LIMIT,
                    user_code_execution=code
                )
                
                command = ["python3", "-c", wrapped_code]
                result = subprocess.run(command,
                                        input=stdin.encode() if stdin else None,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        env=env,
                                        check=False,
                                        timeout=timeout)
            else:
                with NamedTemporaryFile(suffix='.py', delete=False) as tmp:
                    tmp_name = tmp.name
                    tmp.write(code.encode())
                    tmp.flush()
                    
                    # Create a wrapper script that sets resource limits and imports the user code
                    wrapper_code = RESOURCE_LIMIT_WRAPPER.format(
                        memory_limit=MEMORY_LIMIT_BYTES,
                        file_size_limit=FILE_SIZE_LIMIT,
                        max_processes=MAX_PROCESSES,
                        max_open_files=MAX_OPEN_FILES,
                        cpu_time_limit=CPU_TIME_LIMIT,
                        user_code_execution=f"exec(open('{tmp_name}').read())"
                    )
                    
                    wrapper_path = tmp_name + ".wrapper.py"
                    with open(wrapper_path, "w") as f:
                        f.write(wrapper_code)
                    
                    command = ["python3", wrapper_path]
                    result = subprocess.run(command,
                                            input=stdin.encode() if stdin else None,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            env=env,
                                            check=False,
                                            timeout=timeout)
                    
                    # Clean up the temporary files
                    try:
                        os.unlink(tmp_name)
                        os.unlink(wrapper_path)
                    except:
                        pass

        stderr = result.stderr.decode().strip()
        stdout = result.stdout.decode()

        if result.returncode == 0:
            return True, stdout
        return False, _ERROR_MSG_PREFIX + f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
    
    except subprocess.TimeoutExpired:
        # 处理超时异常
        return False, _ERROR_MSG_PREFIX + f"Execution timed out after {timeout} seconds."
    finally:
        # Clean up the temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
