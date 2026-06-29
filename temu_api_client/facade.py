"""
Temu Open Platform API — Facade (Facade Pattern)

WHY: Single entry point for all Temu API operations. Scripts import TemuClient
instead of wiring repositories manually. Each resource handles one domain.

Supports two modes:
  - Normal: client.catalog.get_detail(goods_id)
  - Batch:  client.batch(workers=60, api_concurrency=30) for parallel operations

Usage:
    # Normal
    with TemuClient() as client:
        detail = client.catalog.get_detail(goods_id)
        client.compliance.edit(goods_id, ...)

    # Batch — throttled parallel operations
    with TemuClient() as client:
        batch = client.batch(workers=60, api_concurrency=30)
        batch.catalog.partial_update(payload)  # semaphore-limited
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .core.logging_config import ensure_logging
from .http.client import TemuHTTPClient
from .resources.catalog    import CatalogRepository
from .resources.compliance import ComplianceRepository
from .resources.inventory  import InventoryRepository
from .resources.orders     import OrderRepository
from .resources.shipping   import ShippingRepository


class _ThrottledHTTPClient:
    """Wraps TemuHTTPClient with a semaphore for batch operations.

    WHY: Temu returns 429 or 'System error' when too many concurrent calls
    hit the API. The semaphore limits how many threads can call the API
    simultaneously, while allowing more workers for CPU-bound prep work.
    """

    def __init__(self, client: TemuHTTPClient, max_concurrent: int) -> None:
        self._client = client
        self._semaphore = threading.Semaphore(max_concurrent)

    def call(self, action: str, params: dict | None = None) -> dict:
        with self._semaphore:
            return self._client.call(action, params)

    # Proxy remaining attributes to underlying client
    def __getattr__(self, name):
        return getattr(self._client, name)


class BatchExecutor:
    """Batch execution context with throttled repositories.

    WHY: Batch scripts need ThreadPoolExecutor + semaphore + stats tracking.
    This was duplicated in every script. BatchExecutor centralizes it.

    Usage:
        with client.batch(workers=60, api_concurrency=30) as batch:
            results = batch.map(products, fix_one_product)
    """

    def __init__(self, client: TemuHTTPClient, workers: int, api_concurrency: int) -> None:
        self._throttled = _ThrottledHTTPClient(client, api_concurrency)
        self._workers = workers

        self.catalog    = CatalogRepository(self._throttled)
        self.compliance = ComplianceRepository(self._throttled)

    def map(self, items: list, fn, label: str = "batch") -> dict:
        """Apply fn to each item in parallel. Returns stats dict.

        fn signature: fn(item, catalog, compliance) -> (status, message)
        status should be "ok", "error", or "skip".
        """
        stats = {"ok": 0, "errors": 0, "skip": 0}
        lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            futures = {
                pool.submit(fn, item, self.catalog, self.compliance): item
                for item in items
            }
            done = 0
            for future in as_completed(futures):
                status, msg = future.result()
                with lock:
                    stats[status] = stats.get(status, 0) + 1
                    done += 1
                if done <= 10 or done % 500 == 0 or status == "error":
                    print(f"  [{done}/{len(items)}] {msg}", flush=True)

        return stats


class TemuClient:
    """
    Facade for the Temu Open Platform API.

    Resources:
      client.catalog    → CatalogRepository (products, SKUs, images, attributes)
      client.compliance → ComplianceRepository (EU compliance, GPSR)
      client.orders     → OrderRepository
      client.inventory  → InventoryRepository
      client.shipping   → ShippingRepository

    Batch mode:
      batch = client.batch(workers=60, api_concurrency=30)
      batch.catalog.partial_update(...)  # throttled
      batch.map(items, process_fn)       # parallel with stats
    """

    def __init__(
        self,
        save_responses: bool = False,
        max_retries: int = 5,
        timeout: int = 15,
    ) -> None:
        ensure_logging()
        self._http = TemuHTTPClient(
            save_responses=save_responses,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.catalog    = CatalogRepository(self._http)
        self.compliance = ComplianceRepository(self._http)
        self.orders     = OrderRepository(self._http)
        self.inventory  = InventoryRepository(self._http)
        self.shipping   = ShippingRepository(self._http)

    def batch(self, workers: int = 60, api_concurrency: int = 30) -> BatchExecutor:
        """Create a batch executor with throttled API access.

        Args:
            workers: number of threads in ThreadPoolExecutor
            api_concurrency: max concurrent API calls (semaphore)

        Tested limits (2026-06-29):
          8 concurrent: safe for partial.update
          30 concurrent: safe for most endpoints
          50 concurrent: safe for compliance.edit
        """
        return BatchExecutor(self._http, workers, api_concurrency)

    @property
    def http(self) -> TemuHTTPClient:
        """Direct HTTP client access for endpoints not covered by repositories."""
        return self._http

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "TemuClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
