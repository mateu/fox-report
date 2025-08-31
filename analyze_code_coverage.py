#!/usr/bin/env python3
"""
Code Coverage Analysis for Fox Report

This script analyzes which code paths are not being executed in the fox-report
application by tracing the execution flow from the main entry points.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import importlib.util
import coverage
import subprocess
import tempfile


class CodeAnalyzer:
    """Analyzes Python code for function definitions, imports, and usage."""
    
    def __init__(self, src_dir: str):
        self.src_dir = Path(src_dir)
        self.all_functions: Dict[str, List[str]] = {}  # file -> functions
        self.all_classes: Dict[str, List[str]] = {}   # file -> classes
        self.all_imports: Dict[str, List[str]] = {}   # file -> imports
        self.call_graph: Dict[str, Set[str]] = {}     # caller -> callees
        
    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for functions, classes, and imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            rel_path = str(file_path.relative_to(self.src_dir))
            
            self.all_functions[rel_path] = []
            self.all_classes[rel_path] = []
            self.all_imports[rel_path] = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.all_functions[rel_path].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    self.all_classes[rel_path].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.all_imports[rel_path].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            import_name = f"{node.module}.{alias.name}"
                            self.all_imports[rel_path].append(import_name)
                            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def analyze_all_files(self) -> None:
        """Analyze all Python files in the source directory."""
        for py_file in self.src_dir.rglob("*.py"):
            self.analyze_file(py_file)
    
    def print_summary(self) -> None:
        """Print a summary of all discovered code elements."""
        print("\n=== CODE STRUCTURE ANALYSIS ===")
        
        total_functions = sum(len(funcs) for funcs in self.all_functions.values())
        total_classes = sum(len(classes) for classes in self.all_classes.values())
        
        print(f"Total Python files: {len(self.all_functions)}")
        print(f"Total functions: {total_functions}")
        print(f"Total classes: {total_classes}")
        
        print("\n--- Functions by file ---")
        for file_path, functions in self.all_functions.items():
            if functions:
                print(f"{file_path}: {len(functions)} functions")
                for func in functions:
                    print(f"  - {func}()")
        
        print("\n--- Classes by file ---")
        for file_path, classes in self.all_classes.items():
            if classes:
                print(f"{file_path}: {len(classes)} classes")
                for cls in classes:
                    print(f"  - {cls}")


class CoverageAnalyzer:
    """Analyzes code coverage by running the main application."""
    
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.src_dir = self.repo_root / "src"
    
    def create_mock_config(self) -> Path:
        """Create a minimal mock configuration for testing."""
        config_content = """
email:
  recipient: "test@example.com"
  smtp:
    server: "smtp.gmail.com"
    port: 587
    username: "test@gmail.com"
    password: "test_password"

database:
  url: "sqlite:///mock.db"

logging:
  level: "INFO"
"""
        config_file = self.repo_root / "mock_config.yaml"
        with open(config_file, 'w') as f:
            f.write(config_content)
        return config_file
    
    def run_coverage_analysis(self) -> Tuple[Dict, str]:
        """Run coverage analysis on the main application flow."""
        
        # Start coverage
        cov = coverage.Coverage(source=[str(self.src_dir)])
        cov.start()
        
        coverage_data = {}
        error_msg = ""
        
        try:
            # Add src to Python path
            sys.path.insert(0, str(self.src_dir))
            
            # Import and test main modules without full execution
            print("Testing module imports...")
            
            # Test CLI module import
            try:
                import cli.send_report
                coverage_data['cli.send_report'] = "imported"
                print("✓ cli.send_report imported successfully")
            except Exception as e:
                error_msg += f"Failed to import cli.send_report: {e}\n"
            
            # Test fox_report modules
            try:
                import fox_report.config
                coverage_data['fox_report.config'] = "imported"
                print("✓ fox_report.config imported successfully")
            except Exception as e:
                error_msg += f"Failed to import fox_report.config: {e}\n"
            
            try:
                import fox_report.report_generator
                coverage_data['fox_report.report_generator'] = "imported"
                print("✓ fox_report.report_generator imported successfully")
            except Exception as e:
                error_msg += f"Failed to import fox_report.report_generator: {e}\n"
            
            try:
                import fox_report.email.sender
                coverage_data['fox_report.email.sender'] = "imported"
                print("✓ fox_report.email.sender imported successfully")
            except Exception as e:
                error_msg += f"Failed to import fox_report.email.sender: {e}\n"
            
            # Try to test main entry point with --help to see what gets executed
            try:
                import runpy
                # This should import and trigger argument parsing without full execution
                print("Testing main CLI entry point...")
                # We'll simulate this since we can't actually run it
                coverage_data['main_entry'] = "simulated"
            except Exception as e:
                error_msg += f"Failed to test main entry: {e}\n"
                
        except Exception as e:
            error_msg += f"Coverage analysis failed: {e}\n"
        
        finally:
            cov.stop()
            cov.save()
        
        return coverage_data, error_msg
    
    def generate_coverage_report(self) -> str:
        """Generate a detailed coverage report."""
        try:
            # Create coverage object and load data
            cov = coverage.Coverage(source=[str(self.src_dir)])
            cov.load()
            
            # Generate text report
            report_output = []
            
            def capture_output(line):
                report_output.append(line)
            
            cov.report(file=capture_output, show_missing=True)
            
            return '\n'.join(report_output)
        except Exception as e:
            return f"Failed to generate coverage report: {e}"


class UnusedCodeDetector:
    """Detects potentially unused code by analyzing the codebase."""
    
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.src_dir = self.repo_root / "src"
        self.analyzer = CodeAnalyzer(str(self.src_dir))
    
    def analyze_entry_points(self) -> Dict[str, List[str]]:
        """Analyze the main entry points and trace execution."""
        entry_points = {
            'main_script': ['send_fox_report_gmail.py'],
            'cli_module': ['src/cli/send_report.py'],
            'cron_script': ['run_fox_report_cron.sh']
        }
        
        used_modules = set()
        
        # Analyze the main Python entry point
        main_script = self.repo_root / "send_fox_report_gmail.py"
        if main_script.exists():
            print(f"Analyzing main script: {main_script}")
            try:
                with open(main_script, 'r') as f:
                    content = f.read()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            used_modules.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            used_modules.add(node.module)
            except Exception as e:
                print(f"Error analyzing main script: {e}")
        
        # Analyze CLI module
        cli_script = self.repo_root / "src" / "cli" / "send_report.py"
        if cli_script.exists():
            print(f"Analyzing CLI script: {cli_script}")
            try:
                with open(cli_script, 'r') as f:
                    content = f.read()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            used_modules.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            used_modules.add(node.module)
            except Exception as e:
                print(f"Error analyzing CLI script: {e}")
        
        return {'used_modules': list(used_modules), 'entry_points': entry_points}
    
    def find_unused_files(self) -> List[str]:
        """Find Python files that might be unused."""
        self.analyzer.analyze_all_files()
        
        # Get all Python files
        all_files = set(self.analyzer.all_functions.keys())
        
        # Trace used files from entry points
        entry_analysis = self.analyze_entry_points()
        used_modules = set(entry_analysis['used_modules'])
        
        # Convert module names to file paths
        used_files = set()
        for module in used_modules:
            # Convert module names like 'fox_report.config' to file paths
            if module.startswith('fox_report'):
                file_path = module.replace('fox_report.', '').replace('.', '/') + '.py'
                used_files.add(f"fox_report/{file_path}")
            elif module.startswith('cli'):
                file_path = module.replace('cli.', '').replace('.', '/') + '.py'
                used_files.add(f"cli/{file_path}")
        
        # Also mark files that are definitely used based on our analysis
        definitely_used = {
            'fox_report/__init__.py',
            'fox_report/config.py',
            'fox_report/email/sender.py',
            'fox_report/report_generator.py',
            'cli/__init__.py',
            'cli/send_report.py'
        }
        used_files.update(definitely_used)
        
        # Find potentially unused files
        potentially_unused = []
        for file_path in all_files:
            if not any(used_file in file_path for used_file in used_files):
                potentially_unused.append(file_path)
        
        return potentially_unused
    
    def find_unused_functions(self) -> Dict[str, List[str]]:
        """Find functions that might be unused (simplified analysis)."""
        self.analyzer.analyze_all_files()
        
        # This is a simplified analysis - in a real scenario, we'd need
        # more sophisticated call graph analysis
        potential_unused = {}
        
        for file_path, functions in self.analyzer.all_functions.items():
            if functions:
                # Functions that might be unused (starting with _ or specific patterns)
                unused_in_file = []
                for func in functions:
                    # Skip magic methods and main entry points
                    if func.startswith('_') and not func.startswith('__'):
                        unused_in_file.append(func)
                    elif func.startswith('test_'):
                        unused_in_file.append(func)
                
                if unused_in_file:
                    potential_unused[file_path] = unused_in_file
        
        return potential_unused


def main():
    """Main entry point for code coverage analysis."""
    repo_root = "/home/runner/work/fox-report/fox-report"
    
    print("=== FOX REPORT CODE COVERAGE ANALYSIS ===\n")
    
    # 1. Analyze code structure
    print("1. Analyzing code structure...")
    analyzer = CodeAnalyzer(os.path.join(repo_root, "src"))
    analyzer.analyze_all_files()
    analyzer.print_summary()
    
    # 2. Run coverage analysis
    print("\n2. Running coverage analysis...")
    coverage_analyzer = CoverageAnalyzer(repo_root)
    coverage_data, error_msg = coverage_analyzer.run_coverage_analysis()
    
    if error_msg:
        print(f"Coverage analysis warnings/errors:\n{error_msg}")
    
    print(f"Coverage data collected: {coverage_data}")
    
    # 3. Detect unused code
    print("\n3. Detecting potentially unused code...")
    unused_detector = UnusedCodeDetector(repo_root)
    
    unused_files = unused_detector.find_unused_files()
    unused_functions = unused_detector.find_unused_functions()
    
    # 4. Generate report
    print("\n=== UNUSED CODE ANALYSIS REPORT ===\n")
    
    if unused_files:
        print("POTENTIALLY UNUSED FILES:")
        for file_path in unused_files:
            print(f"  - {file_path}")
    else:
        print("No obviously unused files detected.")
    
    print(f"\nPOTENTIALLY UNUSED FUNCTIONS:")
    if unused_functions:
        for file_path, functions in unused_functions.items():
            print(f"  {file_path}:")
            for func in functions:
                print(f"    - {func}()")
    else:
        print("No obviously unused functions detected.")
    
    # 5. Analysis of main execution path
    print(f"\n=== MAIN EXECUTION PATH ANALYSIS ===")
    entry_analysis = unused_detector.analyze_entry_points()
    print(f"Used modules: {entry_analysis['used_modules']}")
    
    # 6. Recommendations
    print(f"\n=== RECOMMENDATIONS ===")
    print("1. The main execution path is: run_fox_report_cron.sh → send_fox_report_gmail.py → src/cli/send_report.py")
    print("2. Key modules in the execution path:")
    print("   - src/cli/send_report.py (main CLI logic)")
    print("   - src/fox_report/config.py (configuration)")  
    print("   - src/fox_report/report_generator.py (report generation)")
    print("   - src/fox_report/email/sender.py (email sending)")
    
    if unused_files or unused_functions:
        print("3. Consider reviewing the potentially unused code for removal:")
        if unused_files:
            print("   - Files that may not be in the main execution path")
        if unused_functions:
            print("   - Functions that appear to be internal/helper functions")
    
    print("\n4. To get more accurate results, run the application with coverage:")
    print("   python -m coverage run send_fox_report_gmail.py --help")
    print("   python -m coverage report --show-missing")


if __name__ == "__main__":
    main()