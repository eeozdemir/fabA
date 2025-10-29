from fastapi import FastAPI, Response, Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

app = FastAPI(
    title="FABA DevSecOps Case - FastAPI",
    version="1.0.0",
)

REQ_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["path", "method", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency by path in seconds", ["path"]
)

@app.get("/predict")
def predict():
    # Statik skor (case gereği)
    return {"score": 0.87}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    # Basit readiness (örneğin: DB bağlantısı yoksa burada kontrol edebilirdik)
    return {"status": "ready"}

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    LATENCY.labels(request.url.path).observe(time.time() - start)
    REQ_COUNT.labels(request.url.path, request.method, str(response.status_code)).inc()
    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)