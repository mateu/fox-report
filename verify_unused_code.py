#!/usr/bin/env python3
"""
Verification script to validate unused code findings.

This script checks for any hidden references to the modules identified as unused.
"""

import os
import re
from pathlib import Path


def search_for_references(repo_root: str, target_modules: list):
    """Search for any references to target modules in the codebase."""

    repo_path = Path(repo_root)
    results = {}

    for module in target_modules:
        print(f"\n=== Searching for references to '{module}' ===")
        results[module] = {
            'imports': [],
            'string_references': [],
            'file_references': []
        }

        # Search all Python files
        for py_file in repo_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Check for import statements
                import_patterns = [
                    rf'from.*{re.escape(module)}.*import',
                    rf'import.*{re.escape(module)}',
                    rf'from.*{re.escape(module.replace("/", "."))}.*import',
                    rf'import.*{re.escape(module.replace("/", "."))}'
                ]

                for i, line in enumerate(lines, 1):
                    for pattern in import_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            results[module]['imports'].append(
                                f"{py_file}:{i} - {line.strip()}"
                            )

                    # Check for string references
                    if module in line and 'import' not in line:
                        results[module]['string_references'].append(
                            f"{py_file}:{i} - {line.strip()}"
                        )

            except Exception as e:
                print(f"Error reading {py_file}: {e}")

        # Check shell scripts
        for sh_file in repo_path.rglob("*.sh"):
            try:
                with open(sh_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if module in content:
                        results[module]['file_references'].append(str(sh_file))
            except Exception as e:
                print(f"Error reading {sh_file}: {e}")

        # Report findings
        if results[module]['imports']:
            print(f"  IMPORTS FOUND:")
            for ref in results[module]['imports']:
                print(f"    {ref}")
        else:
            print(f"  ✓ No import references found")

        if results[module]['string_references']:
            print(f"  STRING REFERENCES:")
            for ref in results[module]['string_references'][:5]:  # Limit output
                print(f"    {ref}")
            if len(results[module]['string_references']) > 5:
                print(f"    ... and {len(results[module]['string_references']) - 5} more")

        if results[module]['file_references']:
            print(f"  FILE REFERENCES:")
            for ref in results[module]['file_references']:
                print(f"    {ref}")

    return results


def verify_main_execution_path(repo_root: str):
    """Verify the main execution path by tracing imports."""

    print("\n=== VERIFYING MAIN EXECUTION PATH ===\n")

    repo_path = Path(repo_root)

    # Start from main entry point
    main_script = repo_path / "send_fox_report_gmail.py"
    if main_script.exists():
        print(f"1. Entry Point: {main_script}")
        with open(main_script, 'r') as f:
            content = f.read()

        # Find runpy call
        if 'runpy.run_module("cli.send_report"' in content:
            print(f"   → Executes: cli.send_report module")

            # Check CLI module
            cli_module = repo_path / "src" / "cli" / "send_report.py"
            if cli_module.exists():
                print(f"   → Loads: {cli_module}")

                with open(cli_module, 'r') as f:
                    cli_content = f.read()

                # Find fox_report imports
                fox_imports = re.findall(r'from fox_report\.(\S+) import', cli_content)
                print(f"   → Imports fox_report modules: {fox_imports}")

                for module in fox_imports:
                    module_file = repo_path / "src" / "fox_report" / f"{module.replace('.', '/')}.py"
                    if module_file.exists():
                        print(f"     ✓ {module_file} (exists)")
                    else:
                        print(f"     ✗ {module_file} (missing)")


def main():
    """Main verification function."""
    repo_root = "/home/runner/work/fox-report/fox-report"

    print("=== FOX REPORT UNUSED CODE VERIFICATION ===")

    # Modules identified as potentially unused
    target_modules = [
        "cli.py",           # Alternative CLI
        "emailer.py",       # Legacy emailer  
        "time_resolver.py", # Time resolver
        "fox_report/cli",   # Module path variations
        "fox_report.cli",
        "fox_report/emailer",
        "fox_report.emailer",
        "fox_report/time_resolver", 
        "fox_report.time_resolver"
    ]

    # Search for any references
    results = search_for_references(repo_root, target_modules)

    # Verify main execution path
    verify_main_execution_path(repo_root)

    print(f"\n=== VERIFICATION SUMMARY ===")

    unused_confirmed = []
    potentially_used = []

    key_modules = ["cli.py", "emailer.py", "time_resolver.py"]

    for module in key_modules:
        has_imports = bool(results.get(module, {}).get('imports', []))
        has_refs = bool(results.get(module, {}).get('string_references', []))

        if not has_imports and not has_refs:
            unused_confirmed.append(module)
        else:
            potentially_used.append(module)

    print(f"\n✅ CONFIRMED UNUSED:")
    for module in unused_confirmed:
        print(f"   - {module}")

    if potentially_used:
        print(f"\n⚠️  POTENTIALLY USED (needs manual review):")
        for module in potentially_used:
            print(f"   - {module}")

    print(f"\n📊 STATISTICS:")
    print(f"   Modules confirmed unused: {len(unused_confirmed)}")
    print(f"   Modules needing review: {len(potentially_used)}")

    if unused_confirmed:
        print(f"\n🗑️  SAFE TO REMOVE:")
        for module in unused_confirmed:
            module_path = f"src/fox_report/{module}"
            print(f"   rm {module_path}")


if __name__ == "__main__":
    main()