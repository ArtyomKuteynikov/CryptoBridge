import asyncio
import datetime
import time
from collections import defaultdict

import aiohttp
from aiohttp import web


class RateLimiter:
    def __init__(self, requests_per_second=1, cleanup_interval=60):
        self.requests_per_second = requests_per_second
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = datetime.datetime.now()

    async def cleanup_old_records(self):
        now = datetime.datetime.now()
        if (now - self.last_cleanup).total_seconds() >= self.cleanup_interval:
            async with self.lock:
                current_time = datetime.datetime.now()
                for ip in list(self.requests.keys()):
                    self.requests[ip] = [req_time for req_time in self.requests[ip]
                                         if (current_time - req_time).total_seconds() < 1]
                    if not self.requests[ip]:
                        del self.requests[ip]
                self.last_cleanup = now

    async def is_allowed(self, ip):
        await self.cleanup_old_records()
        async with self.lock:
            now = datetime.datetime.now()
            self.requests[ip] = [req_time for req_time in self.requests[ip]
                                 if (now - req_time).total_seconds() < 1]

            if len(self.requests[ip]) >= self.requests_per_second:
                return False

            self.requests[ip].append(now)
            return True


class LoadBalancer:
    def __init__(self, host='0.0.0.0', port: int = 8000, worker_ports: list = (8001,), rps: int = 10):
        self.host = host
        self.port = port
        self.worker_ports = worker_ports
        self.current_worker = 0
        self.lock = asyncio.Lock()
        self.rate_limiter = RateLimiter(requests_per_second=rps)

    async def get_next_worker(self):
        async with self.lock:
            worker = self.worker_ports[self.current_worker]
            self.current_worker = (self.current_worker + 1) % len(self.worker_ports)
            return worker

    async def handle_request(self, request):
        try:
            client_ip = request.remote
            if not await self.rate_limiter.is_allowed(client_ip):
                return web.json_response(
                    {"error": "Rate limit exceeded. Please try again in 1 second."},
                    status=429
                )

            worker_port = await self.get_next_worker()
            url = f'http://localhost:{worker_port}{request.path_qs}'
            async with aiohttp.ClientSession() as session:
                data = await request.read()
                async with session.request(request.method, url, data=data, headers=dict(request.headers)) as response:
                    response_body = await response.read()
                    return web.Response(
                        body=response_body,
                        status=response.status,
                        headers=dict(response.headers)
                    )

        except Exception as e:
            print(f"Error handling request: {e}")
            return web.json_response({"error": str(e)}, status=500)
