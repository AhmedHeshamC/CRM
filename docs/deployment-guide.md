# 🚀 CRM Backend Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Environment Setup](#environment-setup)
5. [Deployment Strategies](#deployment-strategies)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Monitoring & Observability](#monitoring--observability)
8. [Security & Compliance](#security--compliance)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance & Operations](#maintenance--operations)

---

## Overview

This guide provides comprehensive instructions for deploying the CRM Backend system to production environments using enterprise-grade CI/CD practices, advanced deployment strategies, and robust monitoring.

### Key Features

- **Multi-Environment Support**: Development, Staging, Production
- **Advanced Deployment Strategies**: Blue-Green, Canary, Rolling Updates
- **Zero-Downtime Deployments**: Automated traffic management
- **Comprehensive Monitoring**: Prometheus, Grafana, Alerting
- **Security Hardening**: OWASP compliance, vulnerability scanning
- **Automated Rollback**: Instant rollback capabilities
- **High Availability**: Load balancing, auto-scaling

---

## Prerequisites

### Infrastructure Requirements

#### Kubernetes Cluster
- **Version**: 1.25+
- **Nodes**: Minimum 3 for production
- **Storage**: PersistentVolume support
- **Networking**: CNI with Ingress Controller (nginx/istio)

#### External Services
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Registry**: GitHub Container Registry or equivalent
- **DNS**: Custom domain configuration
- **SSL**: Wildcard certificates (Let's Encrypt recommended)

### Tools & Software

#### Required Tools
```bash
# CLI Tools
kubectl >= 1.25
helm >= 3.10
docker >= 20.10
argocd >= 2.5
gh >= 2.20

# Local Development
python >= 3.11
git >= 2.35
make >= 4.3
```

#### Optional Tools
```bash
# Monitoring
prometheus >= 2.40
grafana >= 9.2
alertmanager >= 0.25

# Security
trivy >= 0.30
falco >= 0.33
opa >= 0.43
```

### Access & Permissions

#### Kubernetes RBAC
- Cluster admin access for initial setup
- Namespace-specific permissions for applications
- Service account for CI/CD automation

#### GitHub Permissions
- Repository write access
- Actions read/write permissions
- Packages read/write permissions
- Environments management access

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Git Repository                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Source Code   │  │   Kubernetes    │  │   Dockerfiles   ││
│  │   (Python/Django)│  │   Manifests     │  │   (Multi-stage) ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions CI/CD                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │    Lint     │ │    Test     │ │  Security   │ │  Build   │ │
│  │             │ │             │ │   Scan      │ │          │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
│                                   │                         │
│                                   ▼                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Docker Build   │  │  Security Scan  │  │  Push to Reg.   ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │ Development │ │   Staging   │ │ Production  │ │ Monitoring│ │
│  │   (dev)     │ │   (stag)    │ │   (prod)    │ │ (Prom/Graf)│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Ingress Layer                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │           nginx-ingress-controller / Istio Gateway      ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │   Web App   │ │   API App   │ │Celery Worker│ │Celery Beat│ │
│  │  (Django)   │ │  (Django)   │ │   (Tasks)   │ │ (Schedule)│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │ PostgreSQL  │ │    Redis    │ │File Storage │ │Monitoring│ │
│  │ (Primary)   │ │  (Cache)    │ │   (PVC)     │ │ (Prometheus)│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Environment Setup

### 1. Kubernetes Namespaces

Create namespaces for different environments:

```bash
# Production namespace
kubectl create namespace production
kubectl label namespace production environment=production

# Staging namespace
kubectl create namespace staging
kubectl label namespace staging environment=staging

# Development namespace
kubectl create namespace development
kubectl label namespace development environment=development

# Monitoring namespace
kubectl create namespace monitoring
kubectl label namespace monitoring environment=monitoring
```

### 2. Service Accounts & RBAC

Create service account for deployment automation:

```yaml
# service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: crm-deployer
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: crm-deployer-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: crm-deployer-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: crm-deployer-role
subjects:
- kind: ServiceAccount
  name: crm-deployer
  namespace: production
```

### 3. Secrets Management

#### Application Secrets

```bash
# Create secrets for production
kubectl create secret generic crm-secrets \
  --from-literal=secret-key="your-secret-key-here" \
  --from-literal=db-name="crm_production" \
  --from-literal=db-user="crm_user" \
  --from-literal=db-password="secure-password" \
  --from-literal=redis-password="redis-password" \
  --from-literal=email-user="smtp-user" \
  --from-literal=email-password="smtp-password" \
  -n production

# Create secrets for staging
kubectl create secret generic crm-secrets \
  --from-literal=secret-key="staging-secret-key" \
  --from-literal=db-name="crm_staging" \
  --from-literal=db-user="crm_staging_user" \
  --from-literal=db-password="staging-password" \
  --from-literal=redis-password="staging-redis-password" \
  -n staging
```

#### Container Registry Secrets

```bash
# Create GitHub Container Registry secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=your-github-username \
  --docker-password=your-github-token \
  --namespace=production
```

### 4. ConfigMaps

Create configuration maps:

```bash
# Production config
kubectl create configmap crm-config \
  --from-literal=db-host="postgres-production" \
  --from-literal=db-port="5432" \
  --from-literal=redis-host="redis-production" \
  --from-literal=redis-port="6379" \
  --from-literal=allowed-hosts="crm.example.com,api.crm.example.com" \
  --from-literal=cors-origins="https://crm.example.com,https://app.crm.example.com" \
  --from-literal=email-host="smtp.gmail.com" \
  --from-literal=email-port="587" \
  -n production
```

### 5. Storage Setup

#### Persistent Volumes

```yaml
# storage.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: crm-media-pvc
  namespace: production
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: crm-logs-pvc
  namespace: production
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: fast-ssd
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: prometheus-production-pvc
  namespace: production
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 200Gi
  storageClassName: fast-ssd
```

---

## Deployment Strategies

### 1. Rolling Update (Default)

Progressive replacement of old pods with new ones.

```bash
# Apply rolling update
kubectl apply -f k8s/production/deployment.yaml

# Monitor rollout status
kubectl rollout status deployment/crm-production -n production

# Check rollout history
kubectl rollout history deployment/crm-production -n production
```

**Characteristics:**
- Gradual replacement
- No downtime (if properly configured)
- Simple to implement
- Risk of mixed versions running simultaneously

### 2. Blue-Green Deployment

Run two identical environments (blue and green) and switch traffic.

```bash
# Apply blue-green deployment
kubectl apply -f k8s/production/blue-green-deployment.yaml

# Monitor preview deployment
kubectl get pods -n production -l role=preview

# Promote new version
kubectl argo rollouts promote crm-production-bluegreen -n production

# Rollback if needed
kubectl argo rollouts undo crm-production-bluegreen -n production
```

**Characteristics:**
- Instant traffic switching
- Zero downtime
- Easy rollback
- Double resource requirements
- Requires load balancer support

### 3. Canary Deployment

Gradually route increasing traffic to new version.

```bash
# Apply canary deployment
kubectl apply -f k8s/production/canary-deployment.yaml

# Monitor canary progress
kubectl argo rollouts get rollout crm-production-canary -n production --watch

# Promote to full traffic (or wait for automatic promotion)
kubectl argo rollouts promote crm-production-canary -n production
```

**Traffic Progression:**
- 5% → 20% → 50% → 100%
- Automated analysis at each step
- Rollback on failure detection

**Characteristics:**
- Gradual traffic increase
- Risk mitigation
- Complex to implement
- Requires advanced traffic management

### 4. A/B Testing

Deploy multiple versions and route traffic based on user characteristics.

```yaml
# A/B Testing with Istio
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: crm-ab-test
spec:
  http:
  - match:
    - headers:
        x-user-group:
          exact: beta
    route:
    - destination:
        host: crm-production
        subset: beta
  - route:
    - destination:
        host: crm-production
        subset: stable
```

---

## CI/CD Pipeline

### Pipeline Overview

The CI/CD pipeline consists of 5 main stages:

1. **Lint & Code Quality**: Black, flake8, mypy, bandit, safety
2. **Testing**: Unit, Integration, Security, Performance tests
3. **Security Scanning**: Semgrep, Trivy, vulnerability assessment
4. **Build & Package**: Docker build, SBOM generation, registry push
5. **Deploy**: Environment-specific deployment with validation

### Pipeline Configuration

The pipeline is defined in `.github/workflows/ci-cd-pipeline.yml` and includes:

- **Parallel Testing**: Multiple Python versions and databases
- **Matrix Builds**: Test across different configurations
- **Quality Gates**: Code coverage, security scan results
- **Automated Promotion**: Environment-specific deployment rules
- **Rollback Automation**: Instant rollback on failure detection

### Pipeline Triggers

```yaml
# Automatic triggers
on:
  push:
    branches: [ main, develop, staging ]
  pull_request:
    branches: [ main, develop ]
  release:
    types: [ published ]

# Manual triggers
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'staging'
      rollback:
        description: 'Rollback deployment'
        required: false
        default: false
        type: boolean
```

### Quality Gates

#### Code Quality
- **Coverage**: Minimum 80%
- **Linting**: Black, flake8, mypy compliance
- **Security**: No critical vulnerabilities

#### Performance
- **Response Time**: < 500ms (95th percentile)
- **Error Rate**: < 1%
- **Resource Usage**: Within defined limits

#### Security
- **Vulnerabilities**: No critical or high severity
- **Compliance**: OWASP Top 10 compliance
- **Secrets**: No exposed secrets

### Environment Promotion Rules

```yaml
# Development → Staging (automatic on main branch)
if: github.ref == 'refs/heads/main' && success()
environment: staging

# Staging → Production (manual approval required)
if: github.ref == 'refs/heads/main' && success()
environment: production
```

### Rollback Strategy

#### Automated Rollback Triggers
- Health check failures (> 5 consecutive)
- Error rate > 5%
- Response time > 2 seconds
- Security scan failures

#### Manual Rollback
```bash
# GitHub Actions
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/owner/repo/actions/workflows/rollback.yml/dispatches \
  -d '{"ref":"main","inputs":{"environment":"production","rollback":"true"}}'

# Kubernetes CLI
kubectl rollout undo deployment/crm-production -n production
kubectl argo rollouts undo crm-production-canary -n production
```

---

## Monitoring & Observability

### Prometheus Metrics

#### Application Metrics
```python
# Custom metrics
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter('django_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('django_request_duration_seconds', 'Request duration')

# Business metrics
USER_REGISTRATIONS = Counter('user_registrations_total', 'Total user registrations')
DEAL_CONVERSIONS = Counter('deal_conversions_total', 'Total deal conversions')
```

#### System Metrics
- CPU and memory usage
- Request/response rates
- Database connection pool
- Redis cache hit rate
- Celery queue length

### Alerting Rules

#### Critical Alerts
```yaml
groups:
- name: crm-critical
  rules:
  - alert: CRMDown
    expr: up{job="crm-production"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "CRM application is down"
      description: "CRM application has been down for more than 2 minutes"

  - alert: HighErrorRate
    expr: rate(django_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"
```

#### Warning Alerts
```yaml
- name: crm-warnings
  rules:
  - alert: HighCPUUsage
    expr: rate(container_cpu_usage_seconds_total{pod=~"crm-.*"}[5m]) * 100 > 80
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "CPU usage is {{ $value }}%"

  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes{pod=~"crm-.*"} / container_spec_memory_limit_bytes * 100 > 90
    for: 10m
    labels:
      severity: critical
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }}%"
```

### Dashboard Configuration

#### Grafana Dashboards

1. **Application Overview**
   - Request rate and latency
   - Error rate by endpoint
   - User activity metrics
   - Database performance

2. **Infrastructure Health**
   - Pod and node status
   - Resource utilization
   - Network I/O
   - Storage usage

3. **Business Metrics**
   - User registrations
   - Deal pipeline metrics
   - Activity completion rates
   - Performance KPIs

### Health Checks

#### Application Health Endpoint
```python
# /health/ endpoint
@api_view(['GET'])
def health_check(request):
    """Comprehensive health check endpoint"""

    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': settings.VERSION,
        'checks': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Redis check
    try:
        redis_client.ping()
        health_status['checks']['redis'] = 'healthy'
    except Exception as e:
        health_status['checks']['redis'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Celery check
    try:
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        health_status['checks']['celery'] = 'healthy' if stats else 'unhealthy'
    except Exception as e:
        health_status['checks']['celery'] = f'unhealthy: {str(e)}'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return Response(health_status, status=status_code)
```

#### Kubernetes Health Probes
```yaml
livenessProbe:
  httpGet:
    path: /health/
    port: http
  initialDelaySeconds: 60
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/
    port: http
  initialDelaySeconds: 30
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

---

## Security & Compliance

### Security Measures

#### Container Security
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

containers:
- name: crm-app
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop:
      - ALL
```

#### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: crm-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: crm
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
```

### Compliance Standards

#### OWASP Top 10 Compliance
1. **Injection Prevention**: Parameterized queries, input validation
2. **Broken Authentication**: JWT tokens, session management
3. **Sensitive Data Exposure**: Encryption at rest and in transit
4. **XML External Entities**: XML parser configuration
5. **Broken Access Control**: RBAC, permission checks
6. **Security Misconfiguration**: Security headers, secure defaults
7. **Cross-Site Scripting**: Output encoding, CSP headers
8. **Insecure Deserialization**: Safe serialization libraries
9. **Components with Known Vulnerabilities**: Dependency scanning
10. **Insufficient Logging & Monitoring**: Comprehensive logging

#### Security Scanning
```yaml
# Container security scan
- name: Trivy Security Scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
    format: 'sarif'
    output: 'trivy-results.sarif'

# Dependency vulnerability scan
- name: Safety Check
  run: safety check --json --output safety-report.json
```

### Certificate Management

#### Let's Encrypt Certificates
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@crm.example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

#### Certificate Renewal
```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: crm-tls-cert
  namespace: production
spec:
  secretName: crm-production-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - crm.example.com
  - api.crm.example.com
  - app.crm.example.com
```

---

## Troubleshooting

### Common Issues

#### 1. Deployment Fails to Start

**Symptoms:**
- Pods stuck in CrashLoopBackOff
- Image pull errors
- Resource constraints

**Solutions:**
```bash
# Check pod status
kubectl get pods -n production -l app=crm

# Check pod logs
kubectl logs -f deployment/crm-production -n production

# Check events
kubectl get events -n production --sort-by=.metadata.creationTimestamp

# Check resource limits
kubectl describe pod <pod-name> -n production
```

#### 2. Health Check Failures

**Symptoms:**
- Pods not ready
- Health check timeouts
- Service connectivity issues

**Solutions:**
```bash
# Check health endpoint locally
curl -f http://localhost:8000/health/

# Check service connectivity
kubectl port-forward svc/crm-production-service 8080:80 -n production
curl http://localhost:8080/health/

# Check network policies
kubectl get networkpolicy -n production
```

#### 3. Database Connection Issues

**Symptoms:**
- Database connection timeouts
- Authentication failures
- Connection pool exhaustion

**Solutions:**
```bash
# Test database connectivity
kubectl run db-test --image=postgres:13 --rm -it --restart=Never \
  -- psql $DATABASE_URL -c "SELECT 1"

# Check database logs
kubectl logs -f deployment/postgres-production -n production

# Check connection pool status
curl http://localhost:8000/metrics | grep db_pool
```

#### 4. Redis Connection Issues

**Symptoms:**
- Cache misses
- Session storage failures
- Celery task queue issues

**Solutions:**
```bash
# Test Redis connectivity
kubectl run redis-test --image=redis:7 --rm -it --restart=Never \
  -- redis-cli -h redis-production ping

# Check Redis metrics
curl http://redis-production:9121/metrics

# Monitor Celery queues
kubectl exec -it deployment/crm-production-celery-worker -n production \
  -- celery -A crm.celery inspect active
```

### Debugging Tools

#### 1. Port Forwarding
```bash
# Forward application port
kubectl port-forward svc/crm-production-service 8000:80 -n production

# Forward monitoring ports
kubectl port-forward svc/prometheus-production 9090:9090 -n production
kubectl port-forward svc/grafana-production 3000:3000 -n production
```

#### 2. Debug Pods
```bash
# Start debug pod
kubectl run debug-pod --image=busybox --rm -it --restart=Never -- \
  /bin/sh

# Debug running pod
kubectl debug -it <pod-name> -n production --image=nicolaka/netshoot -- \
  /bin/bash
```

#### 3. Network Debugging
```bash
# Check network connectivity
kubectl exec -it <pod-name> -n production -- \
  curl -v http://crm-production-service/health/

# Check DNS resolution
kubectl exec -it <pod-name> -n production -- \
  nslookup crm-production-service.production.svc.cluster.local
```

### Log Analysis

#### Application Logs
```bash
# Stream application logs
kubectl logs -f deployment/crm-production -n production

# Filter logs by level
kubectl logs deployment/crm-production -n production | grep ERROR

# Get logs from specific time range
kubectl logs --since=1h deployment/crm-production -n production
```

#### System Logs
```bash
# Kubernetes events
kubectl get events -n production --sort-by=.metadata.creationTimestamp

# Ingress logs
kubectl logs -f deployment/nginx-ingress-controller -n ingress-nginx

# System metrics
kubectl top nodes
kubectl top pods -n production
```

---

## Maintenance & Operations

### Regular Maintenance Tasks

#### Daily
- **Health Checks**: Verify application and system health
- **Log Review**: Check for errors and anomalies
- **Performance Monitoring**: Review response times and resource usage
- **Backup Verification**: Ensure backups are completing successfully

#### Weekly
- **Security Scans**: Run vulnerability scans and review results
- **Capacity Planning**: Monitor resource utilization trends
- **Dependency Updates**: Check for security updates in dependencies
- **Performance Analysis**: Review performance metrics and trends

#### Monthly
- **Security Audits**: Conduct comprehensive security reviews
- **Disaster Recovery Tests**: Test backup and recovery procedures
- **Documentation Updates**: Update operational documentation
- **Architecture Review**: Review and update architecture as needed

### Backup Procedures

#### Database Backups
```yaml
# Automated backup CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: db-backup
  namespace: production
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: db-backup
            image: postgres:13
            command:
            - /bin/bash
            - -c
            - |
              pg_dump $DATABASE_URL | gzip > /backup/backup-$(date +%Y%m%d).sql.gz
              # Upload to S3/Minio
              aws s3 cp /backup/backup-$(date +%Y%m%d).sql.gz s3://crm-backups/
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: crm-secrets
                  key: database-url
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

#### Configuration Backups
```bash
# Backup Kubernetes manifests
kubectl get all,configmaps,secrets,pvc -n production -o yaml > cluster-backup-$(date +%Y%m%d).yaml

# Backup Helm releases
helm list -n production
helm get values crm-production -n production > crm-values-$(date +%Y%m%d).yaml
```

### Scaling Procedures

#### Manual Scaling
```bash
# Scale deployment
kubectl scale deployment crm-production --replicas=6 -n production

# Scale with HPA
kubectl autoscale deployment crm-production \
  --min=4 --max=20 --cpu-percent=70 -n production

# Check HPA status
kubectl get hpa -n production
```

#### Auto-Scaling Configuration
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crm-production-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crm-production
  minReplicas: 4
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### Update Procedures

#### Application Updates
```bash
# Trigger new deployment
kubectl set image deployment/crm-production \
  crm-app=ghcr.io/owner/crm:latest -n production

# Monitor rollout
kubectl rollout status deployment/crm-production -n production

# Check rollout history
kubectl rollout history deployment/crm-production -n production
```

#### Dependencies Updates
```bash
# Update Python dependencies
pip-compile requirements.in

# Update Docker images
docker pull postgres:15
docker pull redis:7-alpine

# Update Kubernetes manifests
kubectl apply -f k8s/production/
```

### Security Maintenance

#### Certificate Renewal
```bash
# Check certificate expiration
kubectl get certificates -n production

# Force certificate renewal
kubectl delete certificate crm-tls-cert -n production

# Verify new certificate
kubectl describe certificate crm-tls-cert -n production
```

#### Password Rotation
```bash
# Update database password
kubectl create secret generic crm-secrets \
  --from-literal=db-password="new-secure-password" \
  --dry-run=client -o yaml | kubectl apply -f - -n production

# Restart application
kubectl rollout restart deployment/crm-production -n production
```

---

## Emergency Procedures

### Incident Response

#### 1. Service Outage
```bash
# Check service status
kubectl get pods -n production -l app=crm
kubectl get events -n production --sort-by=.metadata.creationTimestamp

# Immediate rollback
kubectl rollout undo deployment/crm-production -n production

# Scale up resources
kubectl scale deployment crm-production --replicas=6 -n production
```

#### 2. Data Corruption
```bash
# Stop application
kubectl scale deployment crm-production --replicas=0 -n production

# Restore from backup
kubectl create job --from=cronjob/db-restore manual-restore-$(date +%s) -n production

# Verify data integrity
kubectl run db-verify --image=postgres:13 --rm -it --restart=Never \
  -- psql $DATABASE_URL -c "SELECT COUNT(*) FROM authentication_user;"

# Restart application
kubectl scale deployment crm-production --replicas=4 -n production
```

#### 3. Security Incident
```bash
# Isolate affected services
kubectl patch deployment crm-production -n production -p '{"spec":{"replicas":0}}'

# Enable network logging
kubectl patch networkpolicy crm-network-policy -n production -p '{"spec":{"policyTypes":["Ingress","Egress"],"ingress":[{"from":[{"namespaceSelector":{"matchLabels":{"name":"monitoring"}}}],"ports":[{"protocol":"TCP","port":8000}]}]}}'

# Run security scan
trivy image --exit-code 0 --severity HIGH,CRITICAL ghcr.io/owner/crm:latest

# Update secrets
kubectl create secret generic crm-secrets --from-literal=secret-key="new-secret" --dry-run=client -o yaml | kubectl apply -f - -n production

# Restart services
kubectl scale deployment crm-production --replicas=4 -n production
```

### Communication Procedures

#### Alert Escalation
1. **Level 1**: Automated alerts to on-call engineer
2. **Level 2**: Escalate to team lead if not resolved in 15 minutes
3. **Level 3**: Escalate to management if not resolved in 30 minutes
4. **Level 4**: Incident declared, coordinate response team

#### Status Updates
- **Slack Channel**: #crm-outage
- **Email**: IT team and stakeholders
- **Status Page**: Update external status page
- **Documentation**: Create post-incident report

---

## Conclusion

This deployment guide provides comprehensive procedures for deploying and managing the CRM Backend system in production environments. The guide follows enterprise best practices for:

- **Reliability**: Multi-environment support, automated rollback, health monitoring
- **Scalability**: Auto-scaling, load balancing, resource optimization
- **Security**: OWASP compliance, vulnerability scanning, access control
- **Observability**: Comprehensive monitoring, alerting, and logging
- **Maintainability**: Automated procedures, documentation, regular maintenance

For additional support or questions, refer to the project documentation or contact the development team.

---

**Last Updated**: November 2025
**Version**: 1.0.0
**Maintainer**: CRM Backend Team
**Contact**: dev-team@company.com