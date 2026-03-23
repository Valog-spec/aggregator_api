from prometheus_client import Counter, Gauge, Histogram

http_request_total = Counter(
    "http_request_total", "Total requests", ["method", "endpoint", "status"]
)
http_request_total_seconds = Histogram(
    "http_request_total_seconds",
    "Request duration",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)


events_provider_requests_total = Counter(
    "events_provider_requests_total", "Total events requests", ["endpoint", "status"]
)
events_provider_request_duration_seconds = Histogram(
    "events_provider_request_duration_seconds",
    "Request events duration",
    ["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)


tickets_created_total = Counter("tickets_created_total", " Total created tickets")
tickets_cancelled_total = Counter("tickets_cancelled_total", " Total cancelled tickets")
events_total = Gauge("events_total", "Total number of events in database")


cache_hits_total = Counter("cache_hits_total", "Total cache hits")
cache_misses_total = Counter("cache_misses_total", "Total cache miss")
