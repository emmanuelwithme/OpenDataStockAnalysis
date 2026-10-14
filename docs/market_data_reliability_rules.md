# Market Data Reliability

Batching, throttling, bounded retries, caching, backup data sources, and quality validation.

When data retrieval fails, retain the last validated snapshot with a stale flag. Do not use stale quotes for new trading signals.
