#!/usr/bin/env python3
"""
Detailed Code Path Analysis for Fox Report

This script performs a comprehensive analysis of which code paths are executed
vs not executed in the fox-report application through static analysis.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
import re


class DetailedCodeAnalyzer:
    """Performs detailed static analysis of Python code."""
    
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.src_dir = self.repo_root / "src"
        
        # Store detailed information about each file
        self.file_analysis: Dict[str, Dict] = {}
        
        # Track execution paths
        self.execution_paths: Dict[str, Set[str]] = {}
        
    def analyze_file_details(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single file in detail."""
        analysis = {
            'functions': [],
            'classes': [],
            'imports': [],
            'function_calls': [],
            'decorators': [],
            'if_conditions': [],
            'try_except_blocks': [],
            'lines_of_code': 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            analysis['lines_of_code'] = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'decorators': [ast.dump(d) for d in node.decorator_list],
                        'is_private': node.name.startswith('_'),
                        'is_test': node.name.startswith('test_'),
                        'is_main': node.name == 'main'
                    }
                    analysis['functions'].append(func_info)
                    
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'line': node.lineno,
                        'methods': [],
                        'bases': [ast.dump(base) for base in node.bases]
                    }
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info['methods'].append(item.name)
                    
                    analysis['classes'].append(class_info)
                    
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis['imports'].append({
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno
                        })
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            analysis['imports'].append({
                                'module': f"{node.module}.{alias.name}",
                                'from_module': node.module,
                                'name': alias.name,
                                'alias': alias.asname,
                                'line': node.lineno
                            })
                            
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        analysis['function_calls'].append({
                            'function': node.func.id,
                            'line': node.lineno
                        })
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            analysis['function_calls'].append({
                                'function': f"{node.func.value.id}.{node.func.attr}",
                                'line': node.lineno
                            })
                            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            
        return analysis
    
    def analyze_all_files(self):
        """Analyze all Python files in the repository."""
        # Analyze source files
        for py_file in self.src_dir.rglob("*.py"):
            rel_path = str(py_file.relative_to(self.repo_root))
            self.file_analysis[rel_path] = self.analyze_file_details(py_file)
        
        # Analyze root level Python files
        for py_file in self.repo_root.glob("*.py"):
            rel_path = py_file.name
            self.file_analysis[rel_path] = self.analyze_file_details(py_file)
    
    def trace_execution_paths(self):
        """Trace likely execution paths through the code."""
        print("=== TRACING EXECUTION PATHS ===\n")
        
        # Start from main entry point
        main_entry = "send_fox_report_gmail.py"
        if main_entry in self.file_analysis:
            print(f"1. Entry Point: {main_entry}")
            main_analysis = self.file_analysis[main_entry]
            
            # Find imports and calls
            imports = [imp['module'] for imp in main_analysis['imports']]
            print(f"   Imports: {imports}")
            
            # Trace through CLI module
            cli_module = "src/cli/send_report.py"
            if cli_module in self.file_analysis:
                print(f"\n2. CLI Module: {cli_module}")
                cli_analysis = self.file_analysis[cli_module]
                
                cli_imports = [imp['module'] for imp in cli_analysis['imports'] if 'fox_report' in imp['module']]
                print(f"   Fox Report imports: {cli_imports}")
                
                # Analyze main function in CLI
                main_func = next((f for f in cli_analysis['functions'] if f['name'] == 'main'), None)
                if main_func:
                    print(f"   Main function at line {main_func['line']}")
                
                # Trace through each imported fox_report module
                print(f"\n3. Fox Report Modules:")
                for imp in cli_imports:
                    module_file = self.find_module_file(imp)
                    if module_file and module_file in self.file_analysis:
                        analysis = self.file_analysis[module_file]
                        functions = [f['name'] for f in analysis['functions']]
                        classes = [c['name'] for c in analysis['classes']]
                        print(f"   {module_file}:")
                        print(f"     Functions: {functions}")
                        if classes:
                            print(f"     Classes: {classes}")
    
    def find_module_file(self, module_name: str) -> str:
        """Find the file path for a given module name."""
        if module_name.startswith('fox_report.'):
            # Convert module name to file path
            parts = module_name.split('.')
            if len(parts) == 2:  # fox_report.module
                return f"src/fox_report/{parts[1]}.py"
            elif len(parts) == 3:  # fox_report.email.sender
                return f"src/fox_report/{parts[1]}/{parts[2]}.py"
        return None
    
    def identify_unused_code(self):
        """Identify potentially unused code paths."""
        print("\n=== UNUSED CODE IDENTIFICATION ===\n")
        
        # Get execution path modules
        execution_modules = set()
        main_entry = "send_fox_report_gmail.py"
        cli_module = "src/cli/send_report.py"
        
        if main_entry in self.file_analysis:
            execution_modules.add(main_entry)
            main_imports = [imp['module'] for imp in self.file_analysis[main_entry]['imports']]
            
            if cli_module in self.file_analysis:
                execution_modules.add(cli_module)
                cli_imports = [imp['module'] for imp in self.file_analysis[cli_module]['imports'] 
                              if 'fox_report' in imp['module']]
                
                for imp in cli_imports:
                    module_file = self.find_module_file(imp)
                    if module_file:
                        execution_modules.add(module_file)
        
        # Add known execution path files
        execution_modules.update([
            "src/fox_report/config.py",
            "src/fox_report/report_generator.py", 
            "src/fox_report/email/sender.py",
            "src/fox_report/database_query.py"
        ])
        
        print("Files in main execution path:")
        for module in sorted(execution_modules):
            if module in self.file_analysis:
                analysis = self.file_analysis[module]
                func_count = len(analysis['functions'])
                class_count = len(analysis['classes'])
                print(f"  ✓ {module} ({func_count} functions, {class_count} classes)")
        
        print(f"\nFiles potentially NOT in main execution path:")
        unused_files = []
        for file_path in self.file_analysis:
            if file_path not in execution_modules and not file_path.endswith('__init__.py'):
                unused_files.append(file_path)
        
        for file_path in sorted(unused_files):
            analysis = self.file_analysis[file_path]
            func_count = len(analysis['functions'])
            class_count = len(analysis['classes'])
            loc = analysis['lines_of_code']
            print(f"  ? {file_path} ({func_count} functions, {class_count} classes, {loc} LOC)")
    
    def analyze_function_usage(self):
        """Analyze which functions might be unused."""
        print(f"\n=== FUNCTION USAGE ANALYSIS ===\n")
        
        # Collect all function calls across all files
        all_calls = set()
        for file_path, analysis in self.file_analysis.items():
            for call in analysis['function_calls']:
                all_calls.add(call['function'])
        
        print(f"Total unique function calls found: {len(all_calls)}")
        
        # Find functions that don't appear to be called
        for file_path, analysis in self.file_analysis.items():
            unused_functions = []
            for func in analysis['functions']:
                func_name = func['name']
                
                # Skip special functions
                if func_name.startswith('__'):
                    continue
                
                # Check if function is called
                is_called = any(func_name in call for call in all_calls)
                
                if not is_called:
                    unused_functions.append(func)
            
            if unused_functions:
                print(f"\n{file_path} - potentially unused functions:")
                for func in unused_functions:
                    status = ""
                    if func['is_main']:
                        status = " (main entry point)"
                    elif func['is_test']:
                        status = " (test function)"
                    elif func['is_private']:
                        status = " (private function)"
                    
                    print(f"  - {func['name']}() line {func['line']}{status}")
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report."""
        print(f"\n=== COMPREHENSIVE SUMMARY REPORT ===\n")
        
        total_files = len(self.file_analysis)
        total_functions = sum(len(analysis['functions']) for analysis in self.file_analysis.values())
        total_classes = sum(len(analysis['classes']) for analysis in self.file_analysis.values())
        total_loc = sum(analysis['lines_of_code'] for analysis in self.file_analysis.values())
        
        print(f"Repository Statistics:")
        print(f"  Total Python files: {total_files}")
        print(f"  Total functions: {total_functions}")
        print(f"  Total classes: {total_classes}")
        print(f"  Total lines of code: {total_loc}")
        
        print(f"\nFile Analysis:")
        for file_path, analysis in sorted(self.file_analysis.items()):
            print(f"  {file_path}:")
            print(f"    Functions: {len(analysis['functions'])}")
            print(f"    Classes: {len(analysis['classes'])}")
            print(f"    Imports: {len(analysis['imports'])}")
            print(f"    Lines of code: {analysis['lines_of_code']}")
        
        print(f"\nExecution Path Analysis:")
        print(f"1. Primary execution flow:")
        print(f"   run_fox_report_cron.sh → send_fox_report_gmail.py → src/cli/send_report.py")
        
        print(f"\n2. Core modules in execution path:")
        core_modules = [
            "src/cli/send_report.py",
            "src/fox_report/config.py",
            "src/fox_report/report_generator.py",
            "src/fox_report/email/sender.py",
            "src/fox_report/database_query.py"
        ]
        
        for module in core_modules:
            if module in self.file_analysis:
                analysis = self.file_analysis[module]
                print(f"   - {module} ({len(analysis['functions'])} functions)")
        
        print(f"\n3. Alternative/Legacy modules:")
        legacy_candidates = [
            "src/fox_report/cli.py",
            "src/fox_report/emailer.py", 
            "src/fox_report/time_resolver.py"
        ]
        
        for module in legacy_candidates:
            if module in self.file_analysis:
                analysis = self.file_analysis[module]
                print(f"   - {module} ({len(analysis['functions'])} functions) - potentially legacy")


def main():
    """Main entry point."""
    repo_root = "/home/runner/work/fox-report/fox-report"
    
    print("=== DETAILED FOX REPORT CODE ANALYSIS ===\n")
    
    analyzer = DetailedCodeAnalyzer(repo_root)
    
    print("Analyzing all Python files...")
    analyzer.analyze_all_files()
    
    analyzer.trace_execution_paths()
    analyzer.identify_unused_code()
    analyzer.analyze_function_usage()
    analyzer.generate_summary_report()
    
    print(f"\n=== RECOMMENDATIONS ===")
    print(f"1. Focus on the main execution path for coverage analysis")
    print(f"2. Consider reviewing modules marked as 'potentially NOT in main execution path'")
    print(f"3. Private functions starting with '_' may be internal helpers")
    print(f"4. Test functions are for testing only")
    print(f"5. Run the application with sample data to verify actual usage")
    
    print(f"\nTo run live coverage analysis:")
    print(f"PYTHONPATH=src python3 -m coverage run --source=src send_fox_report_gmail.py --help")
    print(f"python3 -m coverage report --show-missing")


if __name__ == "__main__":
    main()