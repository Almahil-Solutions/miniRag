from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# HTTP requests total
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

# HTTP request duration in seconds
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency (seconds)',
    ['method', 'endpoint']
)

# concurrent in-progress requests
IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Requests currently being processed',
    ['method', 'endpoint']
)

# request/response payload sizes
REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request body size in bytes',
    ['method', 'endpoint']
)

# HTTP response body size in bytes
RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response body size in bytes',
    ['method', 'endpoint']
)

# HTTP request latency summary (complement to histogram)
REQUEST_LATENCY_SUMMARY = Summary(
    'http_request_duration_summary_seconds',
    'HTTP request latency summary',
    ['method']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        endpoint = request.url.path
        method = request.method

        # Track in-progress requests
        IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()

        # Capture request size from headers (zero-cost — no body read)
        req_size = int(request.headers.get("content-length", 0))
        REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(req_size)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=response.status_code).inc()

        IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        REQUEST_LATENCY_SUMMARY.labels(method=method).observe(duration)

        res_size = int(response.headers.get("content-length", 0))
        RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(res_size)

        return response



# Create Metrics Endpoint
def setup_metrics(app: FastAPI):
    """
    Setup Prometheus metrics middleware and internal endpoint.
    Scraped over the backend Docker network by Prometheus.
    """
    app.add_middleware(PrometheusMiddleware)
    
    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
