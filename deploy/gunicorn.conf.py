"""Initial capacity settings are configurable; they are not a capacity approval."""

import os


def positive(name, default, maximum):
    value = os.environ.get(name, str(default))
    if not value.isdecimal() or not 1 <= int(value) <= maximum:
        raise ValueError(f"{name} must be a positive bounded integer")
    return int(value)


bind = "0.0.0.0:8000"
workers = positive("Y3GYM_WORKERS", 1, 16)
threads = positive("Y3GYM_THREADS", 2, 16)
worker_class = "gthread"
timeout = 30
graceful_timeout = 30
keepalive = 5
worker_tmp_dir = "/tmp"
control_socket_disable = True
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
access_log_format = "%(h)s %(m)s %(U)s %(s)s %(L)s"
# Only Caddy can reach the app network endpoint; it overwrites forwarded headers.
forwarded_allow_ips = "*"
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
