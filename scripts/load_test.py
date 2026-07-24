import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


def hit_endpoint(url: str) -> tuple[int, float]:
    start = time.perf_counter()
    try:
        response = requests.get(url, timeout=10)
        return response.status_code, time.perf_counter() - start
    except requests.RequestException:
        return 0, time.perf_counter() - start


def run_load_test(url: str, total_requests: int, concurrency: int):
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(hit_endpoint, url) for _ in range(total_requests)]
        for future in as_completed(futures):
            results.append(future.result())

    statuses = [r[0] for r in results]
    latencies = sorted(r[1] for r in results)
    success = sum(1 for s in statuses if s == 200)

    print(f"Total requests: {total_requests}, concurrency: {concurrency}")
    print(f"Success: {success}/{total_requests} ({success / total_requests * 100:.1f}%)")
    print(f"Latency (s) - min: {latencies[0]:.3f}, median: {latencies[len(latencies)//2]:.3f}, "
          f"p95: {latencies[int(len(latencies)*0.95)]:.3f}, max: {latencies[-1]:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    run_load_test(args.url, args.requests, args.concurrency)
