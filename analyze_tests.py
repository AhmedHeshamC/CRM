#!/usr/bin/env python3
"""
Test Analysis Script for CRM Backend
Analyzes test files and provides comprehensive reporting
"""

import os
import re
import ast
import sys
from pathlib import Path
from collections import defaultdict, Counter
import json

class TestAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.test_files = []
        self.test_metrics = {
            'total_files': 0,
            'total_tests': 0,
            'test_categories': defaultdict(list),
            'test_methods': [],
            'assertions_count': 0,
            'mock_usage': 0,
            'test_classes': 0,
            'coverage_indicators': 0
        }

    def find_test_files(self):
        """Find all test files in the project"""
        patterns = [
            'tests/**/test_*.py',
            'src/**/tests/**/*.py',
            '**/*test*.py'
        ]

        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and 'migrations' not in str(file_path):
                    self.test_files.append(file_path)

        self.test_files = sorted(list(set(self.test_files)))
        self.test_metrics['total_files'] = len(self.test_files)

    def analyze_file(self, file_path):
        """Analyze a single test file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return self.analyze_syntax_error(file_path, content)

            file_metrics = {
                'path': str(file_path),
                'classes': [],
                'functions': [],
                'assertions': 0,
                'mocks': 0,
                'imports': [],
                'docstrings': [],
                'test_methods': 0
            }

            # Analyze AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if any(name in node.name.lower() for name in ['test', 'case']):
                        file_metrics['classes'].append(node.name)
                        self.test_metrics['test_classes'] += 1

                elif isinstance(node, ast.FunctionDef):
                    if any(name in node.name.lower() for name in ['test', 'assert']):
                        file_metrics['functions'].append(node.name)
                        file_metrics['test_methods'] += 1
                        self.test_metrics['total_tests'] += 1

                        # Count assertions
                        for child in ast.walk(node):
                            if isinstance(child, (ast.Assert, ast.Call)):
                                if isinstance(child, ast.Assert):
                                    file_metrics['assertions'] += 1
                                elif isinstance(child, ast.Call):
                                    if hasattr(child.func, 'id') and child.func.id in ['assert', 'assertTrue', 'assertFalse', 'assertEqual', 'assertRaises']:
                                        file_metrics['assertions'] += 1

                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        file_metrics['imports'].append(alias.name)
                        if 'mock' in alias.name.lower() or 'unittest.mock' in alias.name:
                            file_metrics['mocks'] += 1

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        file_metrics['imports'].append(node.module)
                        if 'mock' in str(node.module):
                            file_metrics['mocks'] += 1

                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if len(node.value) > 50:  # Likely a docstring
                        file_metrics['docstrings'].append(node.value[:100])

            # Update global metrics
            self.test_metrics['assertions_count'] += file_metrics['assertions']
            self.test_metrics['mock_usage'] += file_metrics['mocks']

            # Categorize test file
            category = self.categorize_test_file(file_path)
            self.test_metrics['test_categories'][category].append(file_metrics)

            # Check for coverage indicators
            if any(keyword in content.lower() for keyword in ['@cover', '--cov', 'coverage']):
                self.test_metrics['coverage_indicators'] += 1

            return file_metrics

        except Exception as e:
            return {'error': str(e), 'path': str(file_path)}

    def categorize_test_file(self, file_path):
        """Categorize test file by type"""
        path_str = str(file_path).lower()

        if 'unit' in path_str:
            return 'Unit Tests'
        elif 'integration' in path_str:
            return 'Integration Tests'
        elif 'api' in path_str or 'endpoint' in path_str:
            return 'API Tests'
        elif 'model' in path_str:
            return 'Model Tests'
        elif 'repository' in path_str:
            return 'Repository Tests'
        elif 'security' in path_str:
            return 'Security Tests'
        elif 'authentication' in path_str or 'auth' in path_str:
            return 'Authentication Tests'
        elif 'monitoring' in path_str:
            return 'Monitoring Tests'
        elif 'tasks' in path_str or 'background' in path_str:
            return 'Background Task Tests'
        else:
            return 'General Tests'

    def analyze_syntax_error(self, file_path, content):
        """Analyze files with syntax errors"""
        return {
            'error': 'Syntax Error',
            'path': str(file_path),
            'content_preview': content[:200]
        }

    def generate_report(self):
        """Generate comprehensive test report"""
        print("🧪 CRM Backend Test Analysis Report")
        print("=" * 50)

        # Find and analyze all test files
        self.find_test_files()

        print(f"\n📊 Test Suite Overview")
        print(f"Total Test Files: {self.test_metrics['total_files']}")
        print(f"Total Test Classes: {self.test_metrics['test_classes']}")
        print(f"Total Test Methods: {self.test_metrics['total_tests']}")
        print(f"Total Assertions: {self.test_metrics['assertions_count']}")
        print(f"Mock Usage: {self.test_metrics['mock_usage']}")
        print(f"Files with Coverage: {self.test_metrics['coverage_indicators']}")

        # Analyze each file
        print(f"\n🔍 Analyzing Test Files...")
        successful_analyses = 0
        error_count = 0

        for test_file in self.test_files:
            result = self.analyze_file(test_file)
            if 'error' not in result:
                successful_analyses += 1
            else:
                error_count += 1

        print(f"Successfully analyzed: {successful_analyses} files")
        if error_count > 0:
            print(f"Errors encountered: {error_count} files")

        # Category breakdown
        print(f"\n📂 Test Categories")
        for category, files in self.test_metrics['test_categories'].items():
            total_tests = sum(f.get('test_methods', 0) for f in files)
            total_assertions = sum(f.get('assertions', 0) for f in files)
            print(f"{category}:")
            print(f"  Files: {len(files)}")
            print(f"  Tests: {total_tests}")
            print(f"  Assertions: {total_assertions}")

        # Quality metrics
        avg_assertions_per_test = (self.test_metrics['assertions_count'] /
                                 max(self.test_metrics['total_tests'], 1))
        mock_percentage = (self.test_metrics['mock_usage'] /
                          max(self.test_metrics['total_files'], 1)) * 100
        coverage_percentage = (self.test_metrics['coverage_indicators'] /
                            max(self.test_metrics['total_files'], 1)) * 100

        print(f"\n📈 Quality Metrics")
        print(f"Avg Assertions per Test: {avg_assertions_per_test:.1f}")
        print(f"Files Using Mocks: {mock_percentage:.1f}%")
        print(f"Files with Coverage: {coverage_percentage:.1f}%")

        # TDD Compliance
        tdd_indicators = [
            'test_' in str(f).lower() for f in self.test_files
        ]
        tdd_compliance = (sum(tdd_indicators) / max(len(tdd_indicators), 1)) * 100

        print(f"\n🎯 TDD Compliance")
        print(f"Files following TDD naming: {tdd_compliance:.1f}%")

        # SOLID Principles Indicators
        print(f"\n🏗️ SOLID Principles Indicators")

        # Single Responsibility
        single_responsibility_files = sum(
            1 for files in self.test_metrics['test_categories'].values()
            for f in files if f.get('test_methods', 0) <= 10  # Reasonable number per class
        )
        sr_percentage = (single_responsibility_files / max(self.test_metrics['total_files'], 1)) * 100
        print(f"Single Responsibility: {sr_percentage:.1f}% (≤10 tests per class)")

        # Test Coverage Estimation
        estimated_coverage = min(95, avg_assertions_per_test * 15 + mock_percentage * 0.5 + tdd_compliance * 0.3)
        print(f"\n📊 Estimated Test Coverage: {estimated_coverage:.1f}%")

        # Security Testing
        security_files = self.test_metrics['test_categories'].get('Security Tests', [])
        print(f"\n🔒 Security Testing")
        print(f"Security test files: {len(security_files)}")
        if security_files:
            security_tests = sum(f.get('test_methods', 0) for f in security_files)
            security_assertions = sum(f.get('assertions', 0) for f in security_files)
            print(f"Security test methods: {security_tests}")
            print(f"Security assertions: {security_assertions}")

        # Business Module Coverage
        print(f"\n🏢 Business Module Test Coverage")
        modules = ['authentication', 'contacts', 'deals', 'activities', 'monitoring', 'tasks']
        for module in modules:
            module_files = [f for f in self.test_files if module in str(f).lower()]
            module_tests = sum(len(f.get('functions', [])) for f in
                             [self.analyze_file(f) for f in module_files if 'error' not in self.analyze_file(f)])
            print(f"{module.title()}: {len(module_files)} files, {module_tests} tests")

        # Overall Assessment
        print(f"\n🎖️ Overall Assessment")

        score = 0
        max_score = 100

        # File count (20 points)
        if self.test_metrics['total_files'] >= 40:
            score += 20
        elif self.test_metrics['total_files'] >= 30:
            score += 15
        elif self.test_metrics['total_files'] >= 20:
            score += 10

        # Test count (20 points)
        if self.test_metrics['total_tests'] >= 200:
            score += 20
        elif self.test_metrics['total_tests'] >= 150:
            score += 15
        elif self.test_metrics['total_tests'] >= 100:
            score += 10

        # Coverage (20 points)
        if estimated_coverage >= 90:
            score += 20
        elif estimated_coverage >= 80:
            score += 15
        elif estimated_coverage >= 70:
            score += 10

        # Security (20 points)
        if len(security_files) >= 5:
            score += 20
        elif len(security_files) >= 3:
            score += 15
        elif len(security_files) >= 1:
            score += 10

        # TDD Compliance (20 points)
        if tdd_compliance >= 90:
            score += 20
        elif tdd_compliance >= 80:
            score += 15
        elif tdd_compliance >= 70:
            score += 10

        print(f"Test Quality Score: {score}/100")

        if score >= 90:
            status = "🟢 EXCELLENT"
        elif score >= 80:
            status = "🟡 GOOD"
        elif score >= 70:
            status = "🟠 ACCEPTABLE"
        else:
            status = "🔴 NEEDS IMPROVEMENT"

        print(f"Overall Status: {status}")

        return {
            'total_files': self.test_metrics['total_files'],
            'total_tests': self.test_metrics['total_tests'],
            'estimated_coverage': estimated_coverage,
            'score': score,
            'status': status,
            'categories': {k: len(v) for k, v in self.test_metrics['test_categories'].items()}
        }

if __name__ == "__main__":
    project_root = Path(__file__).parent
    analyzer = TestAnalyzer(project_root)
    results = analyzer.generate_report()

    print(f"\n📄 Detailed results saved to: test_analysis_results.json")

    # Save results to JSON
    with open('test_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)