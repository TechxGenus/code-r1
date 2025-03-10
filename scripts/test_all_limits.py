#!/usr/bin/env python3
"""
Test script to verify all resource limits in the Python code execution environment.
This script runs all the individual test scripts for different resource limits.
"""

import os
import sys
import subprocess
import argparse
from rich.console import Console
from rich.panel import Panel

console = Console()

# List of test scripts
TEST_SCRIPTS = [
    "test_memory_limit.py",
    "test_file_limit.py",
    "test_cpu_limit.py",
    "test_other_limits.py"
]

def run_test(script_name, args):
    """Run a single test script and return success status"""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    console.print(Panel(f"Running {script_name}", style="bold blue"))
    
    cmd = [sys.executable, script_path]
    if args.verbose:
        console.print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=not args.verbose
        )
        
        if result.returncode == 0:
            console.print(f"[bold green]✓ {script_name} passed[/bold green]")
            return True
        else:
            console.print(f"[bold red]✗ {script_name} failed (exit code: {result.returncode})[/bold red]")
            if not args.verbose and (result.stdout or result.stderr):
                console.print("[yellow]Output:[/yellow]")
                if result.stdout:
                    console.print(result.stdout.decode())
                if result.stderr:
                    console.print("[red]Error:[/red]")
                    console.print(result.stderr.decode())
            return False
    except Exception as e:
        console.print(f"[bold red]✗ {script_name} failed with exception: {str(e)}[/bold red]")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run all resource limit tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("-s", "--single", help="Run only a specific test script")
    args = parser.parse_args()
    
    console.print(Panel("Python Code Execution Resource Limits Test Suite", style="bold green"))
    
    if args.single:
        if args.single not in TEST_SCRIPTS and not args.single.endswith(".py"):
            args.single += ".py"
        
        if args.single in TEST_SCRIPTS or os.path.exists(os.path.join(os.path.dirname(__file__), args.single)):
            success = run_test(args.single, args)
            sys.exit(0 if success else 1)
        else:
            console.print(f"[bold red]Test script '{args.single}' not found![/bold red]")
            console.print(f"Available test scripts: {', '.join(TEST_SCRIPTS)}")
            sys.exit(1)
    
    # Run all tests
    results = []
    for script in TEST_SCRIPTS:
        success = run_test(script, args)
        results.append((script, success))
    
    # Print summary
    console.print("\n")
    console.print(Panel("Test Summary", style="bold blue"))
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for script, success in results:
        status = "[bold green]PASS[/bold green]" if success else "[bold red]FAIL[/bold red]"
        console.print(f"{script}: {status}")
    
    console.print(f"\nTotal: {len(results)}, Passed: {passed}, Failed: {failed}")
    
    # Return non-zero exit code if any test failed
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main() 