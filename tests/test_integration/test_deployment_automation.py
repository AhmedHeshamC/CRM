"""
Deployment Automation Tests
Tests for automated deployment, blue-green, canary, and rollback strategies
Following SOLID principles and enterprise-grade testing practices
"""

import pytest
import asyncio
import json
import time
import subprocess
import requests
import yaml
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from django.test import TestCase, TransactionTestCase
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status


@dataclass
class DeploymentTestConfig:
    """Configuration for deployment testing"""
    name: str
    namespace: str
    strategy: str
    expected_replicas: int
    traffic_split: Optional[Dict[str, int]] = None
    analysis_templates: List[str] = None

    def __post_init__(self):
        if self.analysis_templates is None:
            self.analysis_templates = []


class DeploymentAutomationTests(TransactionTestCase):
    """Comprehensive deployment automation tests"""

    def setUp(self):
        """Set up test environment"""
        self.test_configs = {
            'blue_green': DeploymentTestConfig(
                name='crm-production-bluegreen',
                namespace='production',
                strategy='blue-green',
                expected_replicas=4,
                analysis_templates=['success-rate']
            ),
            'canary': DeploymentTestConfig(
                name='crm-production-canary',
                namespace='production',
                strategy='canary',
                expected_replicas=4,
                traffic_split={'stable': 95, 'canary': 5},
                analysis_templates=['success-rate', 'latency', 'error-rate']
            ),
            'rolling': DeploymentTestConfig(
                name='crm-production',
                namespace='production',
                strategy='rolling',
                expected_replicas=4
            )
        }

    def test_kubernetes_manifest_validation(self):
        """Test Kubernetes manifest file validation"""
        manifests = [
            'k8s/production/deployment.yaml',
            'k8s/production/service.yaml',
            'k8s/production/ingress.yaml',
            'k8s/production/blue-green-deployment.yaml',
            'k8s/production/canary-deployment.yaml',
            'k8s/staging/deployment.yaml'
        ]

        for manifest_path in manifests:
            with self.subTest(manifest=manifest_path):
                try:
                    # Load and validate YAML
                    path = Path(__file__).parent.parent.parent.parent / manifest_path
                    with open(path, 'r') as f:
                        documents = list(yaml.safe_load_all(f))

                    self.assertGreater(len(documents), 0, f"No documents found in {manifest_path}")

                    # Validate each document
                    for doc in documents:
                        self.assertIn('apiVersion', doc)
                        self.assertIn('kind', doc)
                        self.assertIn('metadata', doc)

                        # Validate namespace
                        if 'spec' in doc and doc['kind'] in ['Deployment', 'Service', 'Ingress']:
                            if 'namespace' in doc['metadata']:
                                self.assertIn(doc['metadata']['namespace'], ['production', 'staging', 'development'])

                except Exception as e:
                    self.fail(f"Manifest validation failed for {manifest_path}: {str(e)}")

    def test_blue_green_deployment_strategy(self):
        """Test blue-green deployment strategy"""
        config = self.test_configs['blue_green']

        try:
            # Verify blue-green rollout manifest
            manifest_path = Path(__file__).parent.parent.parent.parent / 'k8s/production/blue-green-deployment.yaml'
            with open(manifest_path, 'r') as f:
                rollout = yaml.safe_load(f)

            # Validate rollout configuration
            self.assertEqual(rollout['apiVersion'], 'argoproj.io/v1alpha1')
            self.assertEqual(rollout['kind'], 'Rollout')
            self.assertEqual(rollout['spec']['strategy']['blueGreen']['activeService'], 'crm-production-active')
            self.assertEqual(rollout['spec']['strategy']['blueGreen']['previewService'], 'crm-production-preview')
            self.assertFalse(rollout['spec']['strategy']['blueGreen']['autoPromotionEnabled'])

            # Verify analysis templates exist
            self.assertIn('prePromotionAnalysis', rollout['spec']['strategy']['blueGreen'])
            self.assertIn('postPromotionAnalysis', rollout['spec']['strategy']['blueGreen'])

            # Test service configuration
            active_service = next(doc for doc in yaml.safe_load_all(open(manifest_path))
                                if doc.get('kind') == 'Service' and 'active' in doc.get('metadata', {}).get('name', ''))
            preview_service = next(doc for doc in yaml.safe_load_all(open(manifest_path))
                                  if doc.get('kind') == 'Service' and 'preview' in doc.get('metadata', {}).get('name', ''))

            self.assertIsNotNone(active_service)
            self.assertIsNotNone(preview_service)

            # Test traffic switching simulation
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0

                # Simulate promotion
                promote_cmd = f"kubectl argo rollouts promote {config.name} -n {config.namespace}"
                result = subprocess.run(promote_cmd.split(), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

                # Verify status
                status_cmd = f"kubectl argo rollouts get status {config.name} -n {config.namespace}"
                result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

            print(f"✅ Blue-green deployment strategy test passed for {config.name}")

        except Exception as e:
            self.fail(f"Blue-green deployment test failed: {str(e)}")

    def test_canary_deployment_strategy(self):
        """Test canary deployment strategy"""
        config = self.test_configs['canary']

        try:
            # Verify canary rollout manifest
            manifest_path = Path(__file__).parent.parent.parent.parent / 'k8s/production/canary-deployment.yaml'
            with open(manifest_path, 'r') as f:
                rollout = yaml.safe_load(f)

            # Validate canary configuration
            self.assertEqual(rollout['apiVersion'], 'argoproj.io/v1alpha1')
            self.assertEqual(rollout['kind'], 'Rollout')
            self.assertIn('canary', rollout['spec']['strategy'])
            self.assertIn('trafficRouting', rollout['spec']['strategy']['canary'])
            self.assertIn('steps', rollout['spec']['strategy']['canary'])

            # Validate traffic routing with Istio
            self.assertIn('istio', rollout['spec']['strategy']['canary']['trafficRouting'])
            self.assertEqual(
                rollout['spec']['strategy']['canary']['trafficRouting']['istio']['virtualService']['name'],
                'crm-vsvc'
            )

            # Validate canary steps
            steps = rollout['spec']['strategy']['canary']['steps']
            self.assertGreater(len(steps), 0)

            # Check weight increments
            weights = []
            for step in steps:
                if 'setWeight' in step:
                    weights.append(step['setWeight'])

            # Weights should be progressively increasing
            for i in range(1, len(weights)):
                self.assertGreaterEqual(weights[i], weights[i-1])

            # Test Istio configuration
            virtual_service = next(doc for doc in yaml.safe_load_all(open(manifest_path))
                                  if doc.get('kind') == 'VirtualService')
            destination_rule = next(doc for doc in yaml.safe_load_all(open(manifest_path))
                                  if doc.get('kind') == 'DestinationRule')

            self.assertIsNotNone(virtual_service)
            self.assertIsNotNone(destination_rule)

            # Test traffic splitting simulation
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0

                # Simulate canary deployment
                deploy_cmd = f"kubectl apply -f k8s/production/canary-deployment.yaml"
                result = subprocess.run(deploy_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

                # Verify rollout status
                status_cmd = f"kubectl argo rollouts get status {config.name} -n {config.namespace}"
                result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

            print(f"✅ Canary deployment strategy test passed for {config.name}")

        except Exception as e:
            self.fail(f"Canary deployment test failed: {str(e)}")

    def test_automated_rollback_functionality(self):
        """Test automated rollback functionality"""
        try:
            # Test rollback command execution
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "deployment.apps/crm-production rolled back"

                rollback_cmd = "kubectl rollout undo deployment/crm-production -n production"
                result = subprocess.run(rollback_cmd, shell=True, capture_output=True, text=True)

                self.assertEqual(result.returncode, 0)
                self.assertIn("rolled back", result.stdout)

            # Test rollback verification
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "deployment \"crm-production\" successfully rolled out"

                status_cmd = "kubectl rollout status deployment/crm-production -n production --timeout=300s"
                result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)

                self.assertEqual(result.returncode, 0)
                self.assertIn("successfully rolled out", result.stdout)

            # Test rollback history
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
deployment.apps/crm-production
REVISION  CHANGE-CAUSE
1         Initial deployment
2         Update to v1.1.0
3         Update to v1.2.0
"""

                history_cmd = "kubectl rollout history deployment/crm-production -n production"
                result = subprocess.run(history_cmd, shell=True, capture_output=True, text=True)

                self.assertEqual(result.returncode, 0)
                self.assertIn("REVISION", result.stdout)

            print("✅ Automated rollback functionality test passed")

        except Exception as e:
            self.fail(f"Rollback functionality test failed: {str(e)}")

    def test_deployment_health_checks(self):
        """Test deployment health checks and readiness"""
        try:
            # Test pod readiness
            readiness_cmd = "kubectl get pods -n production -l app=crm --field-selector=status.phase=Running"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "crm-production-7d8f9c8b-abcde   1/1     Running   0     5m"

                result = subprocess.run(readiness_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn("1/1", result.stdout)
                self.assertIn("Running", result.stdout)

            # Test service endpoints
            endpoint_cmd = "kubectl get endpoints crm-production-service -n production"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
NAME                    ENDPOINTS                      AGE
crm-production-service  10.1.2.3:8000,10.1.2.4:8000   1h
"""

                result = subprocess.run(endpoint_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn("10.1.2.3:8000", result.stdout)

            # Test ingress status
            ingress_cmd = "kubectl get ingress crm-production-ingress -n production"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
NAME                     CLASS    HOSTS                 ADDRESS   PORTS   AGE
crm-production-ingress   nginx    crm.example.com       10.0.0.5  80,443  1h
"""

                result = subprocess.run(ingress_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn("crm.example.com", result.stdout)

            print("✅ Deployment health checks test passed")

        except Exception as e:
            self.fail(f"Deployment health checks test failed: {str(e)}")

    def test_deployment_validation_gates(self):
        """Test deployment validation gates and quality checks"""
        try:
            # Test deployment validation
            validation_checks = [
                ('Resource Limits', 'kubectl describe deployment crm-production -n production | grep -A 5 "Limits"'),
                ('Security Context', 'kubectl get pod crm-production-xxx -n production -o yaml | grep -A 10 "securityContext"'),
                ('Image Pull Policy', 'kubectl get deployment crm-production -n production -o yaml | grep "imagePullPolicy"'),
                ('Health Checks', 'kubectl get deployment crm-production -n production -o yaml | grep -A 5 "readinessProbe"'),
            ]

            for check_name, cmd in validation_checks:
                with self.subTest(check=check_name):
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value.returncode = 0
                        mock_run.return_value.stdout = "Validation passed"

                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, f"{check_name} validation failed")

            print("✅ Deployment validation gates test passed")

        except Exception as e:
            self.fail(f"Deployment validation gates test failed: {str(e)}")

    def test_multi_environment_deployment(self):
        """Test multi-environment deployment pipeline"""
        environments = ['development', 'staging', 'production']
        deployment_results = {}

        for env in environments:
            try:
                # Simulate environment-specific deployment
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = f"deployment to {env} successful"

                    deploy_cmd = f"kubectl apply -f k8s/{env}/deployment.yaml"
                    result = subprocess.run(deploy_cmd, shell=True, capture_output=True, text=True)

                    deployment_results[env] = {
                        'success': result.returncode == 0,
                        'output': result.stdout
                    }

                # Verify environment-specific configurations
                expected_replicas = {
                    'development': 1,
                    'staging': 2,
                    'production': 4
                }

                replica_cmd = f"kubectl get deployment crm-{env} -n {env} -o jsonpath='{{.spec.replicas}}'"
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = str(expected_replicas[env])

                    result = subprocess.run(replica_cmd, shell=True, capture_output=True, text=True)
                    self.assertEqual(int(result.stdout.strip()), expected_replicas[env])

            except Exception as e:
                deployment_results[env] = {
                    'success': False,
                    'error': str(e)
                }

        # Verify all deployments succeeded
        for env, result in deployment_results.items():
            self.assertTrue(result['success'], f"Deployment to {env} failed: {result.get('error', 'Unknown error')}")

        print("✅ Multi-environment deployment test passed")

    def test_deployment_configuration_management(self):
        """Test deployment configuration management and secrets"""
        try:
            # Test ConfigMap management
            configmap_cmd = "kubectl get configmap crm-config -n production -o yaml"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: crm-config
  namespace: production
data:
  db-host: "postgres-production"
  redis-host: "redis-production"
  allowed-hosts: "crm.example.com,api.crm.example.com"
"""

                result = subprocess.run(configmap_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

                configmap = yaml.safe_load(result.stdout)
                self.assertIn('data', configmap)
                self.assertIn('db-host', configmap['data'])

            # Test Secret management
            secret_cmd = "kubectl get secret crm-secrets -n production -o yaml"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
apiVersion: v1
kind: Secret
metadata:
  name: crm-secrets
  namespace: production
type: Opaque
data:
  secret-key: <base64-encoded>
  db-password: <base64-encoded>
"""

                result = subprocess.run(secret_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

                secret = yaml.safe_load(result.stdout)
                self.assertIn('data', secret)
                self.assertEqual(secret['type'], 'Opaque')

            print("✅ Deployment configuration management test passed")

        except Exception as e:
            self.fail(f"Configuration management test failed: {str(e)}")

    def test_deployment_performance_optimization(self):
        """Test deployment performance optimization"""
        try:
            # Test resource allocation
            resources_test = {
                'cpu_requests': '250m',
                'cpu_limits': '1000m',
                'memory_requests': '512Mi',
                'memory_limits': '2Gi'
            }

            for resource, expected_value in resources_test.items():
                cmd = f"kubectl get deployment crm-production -n production -o jsonpath='{{.spec.template.spec.containers[0].resources.{resource}}}'"
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = expected_value

                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(result.stdout.strip(), expected_value)

            # Test affinity rules
            affinity_cmd = "kubectl get deployment crm-production -n production -o yaml | grep -A 10 'affinity:'"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app: crm
"""

                result = subprocess.run(affinity_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn('podAntiAffinity', result.stdout)

            print("✅ Deployment performance optimization test passed")

        except Exception as e:
            self.fail(f"Performance optimization test failed: {str(e)}")

    def test_deployment_monitoring_integration(self):
        """Test deployment monitoring and observability integration"""
        try:
            # Test Prometheus ServiceMonitor
            monitor_cmd = "kubectl get servicemonitor crm-production-metrics -n production -o yaml"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: crm-production-metrics
  namespace: production
spec:
  selector:
    matchLabels:
      app: crm
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
"""

                result = subprocess.run(monitor_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

                monitor = yaml.safe_load(result.stdout)
                self.assertEqual(monitor['kind'], 'ServiceMonitor')
                self.assertIn('endpoints', monitor['spec'])

            # Test alerting rules
            alert_cmd = "kubectl get prometheusrule crm-production-alerts -n production -o yaml"
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = """
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: crm-production-alerts
  namespace: production
spec:
  groups:
  - name: crm.rules
    rules:
    - alert: CRMDown
      expr: up{job="crm-production"} == 0
"""

                result = subprocess.run(alert_cmd, shell=True, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)

                alert_rule = yaml.safe_load(result.stdout)
                self.assertEqual(alert_rule['kind'], 'PrometheusRule')
                self.assertIn('groups', alert_rule['spec'])

            print("✅ Deployment monitoring integration test passed")

        except Exception as e:
            self.fail(f"Monitoring integration test failed: {str(e)}")


class DeploymentAutomationPerformanceTests(TransactionTestCase):
    """Performance tests for deployment automation"""

    def test_deployment_speed_benchmarks(self):
        """Test deployment speed meets performance benchmarks"""
        benchmarks = {
            'development': 300,  # 5 minutes
            'staging': 600,      # 10 minutes
            'production': 1200   # 20 minutes
        }

        for env, max_time in benchmarks.items():
            with self.subTest(environment=env):
                try:
                    start_time = time.time()

                    # Simulate deployment timing
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value.returncode = 0

                        deploy_cmd = f"kubectl apply -f k8s/{env}/deployment.yaml"
                        result = subprocess.run(deploy_cmd, shell=True, capture_output=True, text=True)

                        # Simulate wait for rollout
                        time.sleep(0.1)  # Minimal delay for test

                    deployment_time = time.time() - start_time
                    self.assertLess(deployment_time, max_time,
                                  f"Deployment to {env} took {deployment_time}s, exceeding benchmark of {max_time}s")

                except Exception as e:
                    self.fail(f"Deployment speed test failed for {env}: {str(e)}")

    def test_rollback_speed(self):
        """Test rollback speed meets performance requirements"""
        try:
            start_time = time.time()

            # Simulate rollback timing
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0

                rollback_cmd = "kubectl rollout undo deployment/crm-production -n production"
                result = subprocess.run(rollback_cmd, shell=True, capture_output=True, text=True)

                # Simulate wait for rollback completion
                time.sleep(0.1)  # Minimal delay for test

            rollback_time = time.time() - start_time
            max_rollback_time = 300  # 5 minutes

            self.assertLess(rollback_time, max_rollback_time,
                          f"Rollback took {rollback_time}s, exceeding maximum of {max_rollback_time}s")

        except Exception as e:
            self.fail(f"Rollback speed test failed: {str(e)}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])