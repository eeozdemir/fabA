# FABA DevSecOps Case (FastAPI)

1.Overview

This project demonstrates a secure, observable, and automated mini-deployment of a FastAPI application — built as part of the FABA DevSecOps Engineer Case.

The goal was not only to make the app work, but to show DevSecOps thinking:
how to containerize securely, automate with CI/CD, and measure reliability with proper observability.

Key features:

- FastAPI microservice (/predict, /healthz, /readyz, /metrics)
- Secure multi-stage Dockerfile (non-root, minimal image)
- Helm Chart for deployment (with probes, resources, HPA, NetworkPolicy)
- GitHub Actions CI pipeline with security checks (Trivy, SBOM, Bandit)
- Prometheus metrics and alert rule for reliability
- Step-by-step reasoning included in this README

2.Architecture Overview

flowchart TD
  A[Client Request] --> B[FastAPI App (/predict)]
  B --> C[Docker Container - Non Root User]
  C --> D[Kubernetes (Helm Deployed)]
  D --> E[/metrics Endpoint -> Prometheus]
  E --> F[Alert Rules (5xx rate > 5%)]
  G[GitHub Actions CI/CD] --> D
  G --> H[Trivy Scan]
  G --> I[SBOM Generation]
  G --> J[Static Code Analysis (Bandit)]


This structure ensures:

- Security at every layer (code, image, runtime)
- Observability through metrics
- Reproducibility and automation via CI/CD and Helm

3.Local Environment Setup (Mac M1 / Local Development)

Since the case allows using local tools, I used Minikube (Docker driver + Calico CNI).
It’s light, ARM64 compatible, and supports real NetworkPolicies and HPA metrics.

- Start Minikube with Calico for network policies
minikube start --driver=docker --cni=calico --cpus=4 --memory=6g

- Enable metrics-server for HPA and observability
minikube addons enable metrics-server

- Optional: enable ingress for future routing
minikube addons enable ingress

Reasoning:
Using Calico enforces real NetworkPolicies, metrics-server enables HPA and latency measurement, and the Docker driver keeps everything inside Docker Desktop (ideal for Mac).

3.1 Kubernetes Dashboard Access (Optional)

For visual cluster management and real-time monitoring, you can enable the Kubernetes Dashboard in Minikube.
This provides a browser-based interface to view Pods, Services, HPA activity, and even Prometheus/Grafana components.

1- Enable the Dashboard

Minikube already includes the Dashboard as an addon:

minikube addons enable dashboard

2- Launch the Dashboard

Start the Dashboard service locally and open it in your browser:

minikube dashboard


This command sets up a local proxy and usually opens a URL like:

http://127.0.0.1:xxxxx/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/

3️- Secure Login with Token

For a more secure access method:

kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard
kubectl create clusterrolebinding dashboard-admin-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=kubernetes-dashboard:dashboard-admin

kubectl -n kubernetes-dashboard create token dashboard-admin


Copy the generated token and paste it into the Dashboard login screen.

4.Application Design

File: app/main.py

- /predict returns a static response (as requested in the case).
- /healthz and /readyz endpoints allow Kubernetes to check pod health and readiness.
- /metrics exposes Prometheus-compatible metrics.

I also added a middleware to measure:

Request latency
Request count by method/status/path

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    LATENCY.labels(request.url.path).observe(time.time() - start)
    REQ_COUNT.labels(request.url.path, request.method, str(response.status_code)).inc()
    return response


Reasoning:
Adding this middleware allows us to measure p95 latency, request success/failure ratio, and define alert rules later on.

5.Dockerization

File: Dockerfile

I used a multi-stage build and a non-root user for security:

FROM python:3.12-slim AS builder
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --prefix /install

FROM python:3.12-slim
COPY --from=builder /install /usr/local
COPY app/ /app/
RUN useradd -u 10001 -m <username>
USER 10001:10001


Reasoning:

- Multi-stage keeps the image minimal and free of build tools.
- Non-root user (UID 10001) prevents privilege escalation.
- Using python:3.12-slim balances security and speed.

To build:

docker build -t <yourrepo>/fastapi-app:latest .


To run locally:

docker run -p 8000:8000 <yourrepo>/fastapi-app:latest

6.Helm Chart Deployment

I packaged all Kubernetes manifests (Deployment, Service, HPA, NetworkPolicy) inside a Helm chart.
This allows reusable, configurable deployments — ideal for production workflows.

helm install fastapi ./charts/fastapi
kubectl get pods,svc,hpa


Why Helm?

- Reusability: Environment variables and limits in values.yaml
- Readability: One command deploys everything
- Security: Probes, resource limits, and NetworkPolicies are templated and versioned

Key configurations in values.yaml:

probes:
  readinessPath: /readyz
  livenessPath: /healthz
resources:
  limits: { cpu: "500m", memory: "256Mi" }
hpa:
  enabled: true
  cpuAvgUtil: 70
networkPolicy:
  enabled: true
  allowedNamespaces: [default, ingress-nginx]


Reasoning:
Every aspect (readiness, limits, scaling, ingress control) aligns with production-grade Kubernetes practices.

7.CI/CD Security Pipeline (GitHub Actions)

File: .github/workflows/ci.yaml

Pipeline steps:

Build & Push Docker image (multi-arch for ARM64 compatibility)
Trivy Scan → Detect known vulnerabilities
SBOM generation (Syft) → Identify all dependencies for supply chain visibility
Static code analysis (Bandit) → Detect insecure Python code patterns
Upload reports as artifacts → Easy traceability

- name: Trivy Scan
  uses: aquasecurity/trivy-action@master
- name: SBOM (syft)
  run: syft ${{ env.IMAGE }}:${{ env.TAG }} -o json > sbom.json
- name: Bandit
  run: bandit -r app/ -f json -o bandit-report.json


Reasoning:
These three steps — vulnerability scan, SBOM, and SAST — demonstrate supply chain security awareness.
Even though this is a local demo, the same pattern scales to any enterprise pipeline.

8.Observability & Reliability

Prometheus metrics are exposed via /metrics.
This data can be scraped and visualized by Prometheus or Grafana.

Example alert rule (k8s/alert-rules.yaml):

- alert: HighErrorRate
  expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
  for: 2m
  labels: { severity: warning }

SLO Definitions

Metric	         Target	             Description
Availability	    99%	        Percentage of successful requests
p95 Latency	     <250 ms	    95% of requests should respond within 250ms

Reasoning:
Defining measurable SLOs ensures we can link performance metrics to service reliability — this is a fundamental part of modern Site Reliability Engineering (SRE).

8.1 Monitoring & Observability Stack (Prometheus + Grafana)

For observability, a complete monitoring stack was added using Prometheus, Grafana, and the kube-prometheus-stack Helm chart.
This setup allows tracking key metrics such as request rate, latency, and error ratio, helping ensure service reliability and SLO compliance.

All monitoring files are placed inside the monitoring/ directory to keep the observability layer separate from the main application.

- monitoring/values.yaml — defines Helm configuration for Prometheus and Grafana, referencing an existing secret for secure admin credentials.

- monitoring/servicemonitor-fastapi.yaml — instructs Prometheus to automatically discover and scrape the FastAPI /metrics endpoint.

- monitoring/promrule-fastapi.yaml — defines a custom alert rule that triggers when 5xx errors exceed 5% for more than two minutes.

With this setup, Prometheus continuously collects metrics, Grafana visualizes them through dashboards, and Alertmanager notifies when service health degrades.
This completes the observability and reliability aspect of the case with a clean, production-style design.


9.Local Automation (Makefile)

To speed up local testing and scans, I added a Makefile:

build:
	docker build -t yourrepo/fastapi-app:latest .
run:
	docker run -p 8000:8000 yourrepo/fastapi-app:latest
scan:
	trivy image yourrepo/fastapi-app:latest
sbom:
	syft yourrepo/fastapi-app:latest -o json > sbom.json


Reasoning:
This reduces repetitive command typing, enforces consistent local builds, and mirrors what CI does.

10.Security & Compliance Highlights

Tool	                  Purpose	                              Layer
Bandit	           Static code analysis (Python)	           Source code
Trivy	           Image vulnerability scanning	               Container
Syft	           SBOM generation	                           Supply chain
Non-root user	   Prevent privilege escalation	               Runtime
NetworkPolicy	   Restrict ingress/egress traffic	           Cluster
HPA + Probes	   Maintain reliability under load	           Operations

Each tool adds a layer of defense and traceability — a classic DevSecOps principle: shift-left and secure everything.

11.Expected Outputs

After successful deployment:

kubectl get pods,svc,hpa


You’ll see:

- 2 replicas running
- ClusterIP service on port 80
- HPA configured for autoscaling
- NetworkPolicy enforced (Calico)

And visiting:

http://<minikube-ip>:<service-port>/predict


returns:

{"score": 0.87}

12.Supply Chain Integrity (Cosign Signing & Verification)

To complete the security chain, container image signing and verification were implemented using Cosign (Sigstore).
This ensures that every image built by the CI pipeline is both authentic and tamper-proof before being deployed.

The image signing process uses a private key stored securely as a GitHub Secret, while the corresponding public key (cosign.pub) is kept in the repository for verification.
After each build, the image is signed and verified automatically — confirming that it was produced by the trusted CI pipeline and has not been altered.

This step extends the existing security layers of the project:

- Trivy for vulnerability scanning
- Syft (SBOM) for dependency tracking
- Bandit for static code analysis
- Cosign for signature validation and integrity verification

By adding Cosign, the supply chain is now protected end-to-end: from source code, to image build, to deployment.
This provides complete transparency, traceability, and trust across the DevSecOps workflow.

13.Summary

This project shows how DevSecOps is more than CI/CD — it’s security, reliability, and automation woven together.

- I containerized securely → multi-stage, non-root, minimal
- I automated supply chain scans → Trivy, SBOM, Bandit
- I deployed declaratively → Helm Chart + probes + HPA + NetworkPolicy
- I monitored and defined SLOs → Prometheus metrics and alert rules

The end result is a small but production-like system demonstrating real DevSecOps principles from code to cluster.

Author:
Emre Özdemir
DevOps / Cloud / Platform Engineer