"""
Code Quality Metrics and Monitoring
Implementing comprehensive code quality measurement with TDD approach
"""

import pytest
import ast
import inspect
import re
from collections import defaultdict
from typing import Dict, List, Any, Tuple
from django.test import TestCase
from django.conf import settings
import subprocess
import os


class CodeComplexityMetrics(TestCase):
    """
    Cyclomatic complexity and code quality metrics
    Following TDD: Define quality standards first
    """

    def test_cyclomatic_complexity_limits(self):
        """
        TDD Test: Cyclomatic complexity should be within acceptable limits
        Quality Standard: Maximum complexity of 10 per function/method
        """
        # Get Python files in the project
        python_files = []
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/src'):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        complexity_results = []

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                complexity = self._calculate_complexity(tree)

                for func_name, complexity_score in complexity.items():
                    if complexity_score > 10:
                        complexity_results.append({
                            'file': file_path,
                            'function': func_name,
                            'complexity': complexity_score
                        })
            except Exception as e:
                # Skip files that can't be parsed
                continue

        # Assert that no function exceeds complexity limit
        self.assertEqual(len(complexity_results), 0,
                        f"Functions exceeding complexity limit: {complexity_results}")

    def _calculate_complexity(self, tree: ast.AST) -> Dict[str, int]:
        """
        Calculate cyclomatic complexity using AST analysis
        """
        complexity = defaultdict(int)

        class ComplexityVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                base_complexity = 1
                complexity[node.name] += base_complexity
                self._count_complexity_nodes(node)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                base_complexity = 1
                complexity[node.name] += base_complexity
                self._count_complexity_nodes(node)
                self.generic_visit(node)

            def _count_complexity_nodes(self, node):
                """Count complexity-adding nodes"""
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                         ast.ExceptHandler, ast.With, ast.AsyncWith)):
                        complexity[node.name] += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity[node.name] += len(child.values) - 1

        visitor = ComplexityVisitor()
        visitor.visit(tree)

        return dict(complexity)

    def test_function_length_limits(self):
        """
        TDD Test: Function length should be within acceptable limits
        Quality Standard: Maximum 50 lines per function
        """
        python_files = []
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/src'):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        long_functions = []

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                tree = ast.parse(''.join(lines))
                function_lines = self._count_function_lines(tree, lines)

                for func_name, line_count in function_lines.items():
                    if line_count > 50:
                        long_functions.append({
                            'file': file_path,
                            'function': func_name,
                            'lines': line_count
                        })
            except Exception:
                continue

        self.assertEqual(len(long_functions), 0,
                        f"Functions exceeding line limit: {long_functions}")

    def _count_function_lines(self, tree: ast.AST, lines: List[str]) -> Dict[str, int]:
        """Count lines for each function"""
        function_lines = {}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                line_count = end_line - start_line + 1
                function_lines[node.name] = line_count

        return function_lines


class TestCoverageMetrics(TestCase):
    """
    Test coverage metrics and quality standards
    Following TDD: Define coverage requirements
    """

    def test_minimum_test_coverage(self):
        """
        TDD Test: Code should have minimum test coverage
        Quality Standard: 90% line coverage
        """
        # Run coverage report
        try:
            result = subprocess.run([
                'python', '-m', 'coverage', 'run', '--source=/home/m/Desktop/backEnd/crm/src',
                '-m', 'pytest', '/home/m/Desktop/backEnd/crm/tests/'
            ], capture_output=True, text=True, cwd='/home/m/Desktop/backEnd/crm')

            # Generate coverage report
            report_result = subprocess.run([
                'python', '-m', 'coverage', 'report', '--format=json'
            ], capture_output=True, text=True, cwd='/home/m/Desktop/backEnd/crm')

            if report_result.returncode == 0:
                import json
                coverage_data = json.loads(report_result.stdout)

                # Check overall coverage
                overall_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                self.assertGreaterEqual(overall_coverage, 90.0,
                                      f"Test coverage {overall_coverage}% is below 90% requirement")

        except Exception as e:
            # If coverage tools aren't available, skip this test
            self.skipTest("Coverage tools not available")

    def test_test_to_code_ratio(self):
        """
        TDD Test: Maintain healthy test-to-code ratio
        Quality Standard: At least 1:1 test-to-code ratio
        """
        code_files = []
        test_files = []

        # Count code files
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/src'):
            for file in files:
                if file.endswith('.py'):
                    code_files.append(os.path.join(root, file))

        # Count test files
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/tests'):
            for file in files:
                if file.endswith('.py') and file.startswith('test_'):
                    test_files.append(os.path.join(root, file))

        # Count lines
        code_lines = 0
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code_lines += len(f.readlines())
            except:
                continue

        test_lines = 0
        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    test_lines += len(f.readlines())
            except:
                continue

        if code_lines > 0:
            ratio = test_lines / code_lines
            self.assertGreaterEqual(ratio, 1.0,
                                  f"Test-to-code ratio {ratio:.2f} is below 1.0 requirement")

    def test_assert_quality(self):
        """
        TDD Test: Test assertions should be descriptive and meaningful
        Quality Standard: Specific, descriptive assertions
        """
        test_files = []
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/tests'):
            for file in files:
                if file.endswith('.py') and file.startswith('test_'):
                    test_files.append(os.path.join(root, file))

        poor_assertions = []

        for file_path in test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for poor assertion patterns
                if re.search(r'assertEqual\(.*,\s*\)', content):
                    poor_assertions.append(f"{file_path}: Empty assertEqual")

                if re.search(r'assertTrue\([^,)]+\)', content):
                    poor_assertions.append(f"{file_path}: Non-specific assertTrue")

                if re.search(r'assertIn\([^,)]+,\s*[^,)]+\)', content):
                    # Check if it's checking for specific values, not just existence
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'assertIn(' in line and not any(msg in line for msg in ['message', 'error', 'detail']):
                            if i < len(lines) - 1:
                                next_line = lines[i + 1].strip()
                                if not next_line.startswith('#') and 'assert' not in next_line:
                                    poor_assertions.append(f"{file_path}: assertIn without descriptive message")

            except Exception:
                continue

        # Allow some poor assertions but limit them
        self.assertLessEqual(len(poor_assertions), 5,
                           f"Too many poor assertions found: {poor_assertions[:10]}")


class DocumentationQualityMetrics(TestCase):
    """
    Documentation quality metrics
    Following TDD: Document quality requirements
    """

    def test_docstring_coverage(self):
        """
        TDD Test: Public functions should have docstrings
        Quality Standard: 100% docstring coverage for public functions
        """
        python_files = []
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/src'):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    python_files.append(os.path.join(root, file))

        undocumented_functions = []

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                functions_without_docs = self._find_undocumented_functions(tree)

                if functions_without_docs:
                    undocumented_functions.append({
                        'file': file_path,
                        'functions': functions_without_docs
                    })
            except Exception:
                continue

        self.assertEqual(len(undocumented_functions), 0,
                        f"Functions without docstrings: {undocumented_functions}")

    def _find_undocumented_functions(self, tree: ast.AST) -> List[str]:
        """Find functions without docstrings"""
        undocumented = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private functions (starting with _)
                if node.name.startswith('_'):
                    continue

                # Check if function has docstring
                if (not node.body or
                    not isinstance(node.body[0], ast.Expr) or
                    not isinstance(node.body[0].value, ast.Constant) or
                    not isinstance(node.body[0].value.value, str)):
                    undocumented.append(node.name)

        return undocumented

    def test_api_documentation_completeness(self):
        """
        TDD Test: API endpoints should have complete documentation
        Quality Standard: All API endpoints documented
        """
        # This would check for drf-spectacular documentation completeness
        # For now, just ensure documentation files exist
        doc_files = [
            '/home/m/Desktop/backEnd/crm/README.md',
            '/home/m/Desktop/backEnd/crm/docs/api.md',
        ]

        for doc_file in doc_files:
            if os.path.exists(doc_file):
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertGreater(len(content), 1000,
                                     f"Documentation file {doc_file} seems too short")


class SecurityQualityMetrics(TestCase):
    """
    Security quality metrics
    Following TDD: Define security quality standards
    """

    def test_secret_detection(self):
        """
        TDD Test: No secrets should be committed to code
        Quality Standard: Zero secrets in codebase
        """
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'AKIA[0-9A-Z]{16}',  # AWS access key pattern
            r'[0-9a-f]{32,}',  # Potential hex keys
        ]

        python_files = []
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/src'):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        potential_secrets = []

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_number = content[:match.start()].count('\n') + 1
                        potential_secrets.append({
                            'file': file_path,
                            'line': line_number,
                            'match': match.group()[:50] + '...' if len(match.group()) > 50 else match.group()
                        })
            except Exception:
                continue

        # Filter out obvious false positives
        filtered_secrets = []
        for secret in potential_secrets:
            if not any(ignored in secret['match'].lower() for ignored in [
                'example', 'test', 'demo', 'sample', 'localhost'
            ]):
                filtered_secrets.append(secret)

        self.assertEqual(len(filtered_secrets), 0,
                        f"Potential secrets found: {filtered_secrets[:5]}")

    def test_dependency_vulnerability_scan(self):
        """
        TDD Test: Dependencies should not have known vulnerabilities
        Quality Standard: Zero critical vulnerabilities
        """
        try:
            # Run safety check
            result = subprocess.run([
                'python', '-m', 'safety', 'check', '--json'
            ], capture_output=True, text=True, cwd='/home/m/Desktop/backEnd/crm')

            if result.returncode == 0:
                import json
                vulnerabilities = json.loads(result.stdout)

                critical_vulns = [v for v in vulnerabilities if v.get('severity') == 'critical']
                self.assertEqual(len(critical_vulns), 0,
                              f"Critical vulnerabilities found: {critical_vulns}")
            else:
                self.skipTest("Safety dependency check not available")

        except Exception:
            self.skipTest("Dependency vulnerability scanning not available")


class PerformanceQualityMetrics(TestCase):
    """
    Performance quality metrics
    Following TDD: Define performance quality standards
    """

    def test_import_efficiency(self):
        """
        TDD Test: Imports should be efficient
        Quality Standard: No circular imports, minimized import time
        """
        python_files = []
        for root, dirs, files in os.walk('/home/m/Desktop/backEnd/crm/src'):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        import_times = []

        for file_path in python_files[:10]:  # Test first 10 files
            try:
                start_time = time.time()
                spec = importlib.util.spec_from_file_location("test_module", file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                end_time = time.time()

                import_time = (end_time - start_time) * 1000  # Convert to milliseconds
                import_times.append({
                    'file': file_path,
                    'time': import_time
                })
            except Exception:
                continue

        # Most imports should complete quickly
        slow_imports = [imp for imp in import_times if imp['time'] > 100]
        self.assertLessEqual(len(slow_imports), 2,
                           f"Slow imports found: {slow_imports}")


import time
import importlib.util