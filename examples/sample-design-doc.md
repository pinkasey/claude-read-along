# Design: Per-Tenant Rate Limiting for the Public API

Status: Draft for review. Owner: Platform team. Last updated: November 2026.

## Background

Today the public API applies one global rate limit of 2,000 requests per second, shared by every tenant. When a single large tenant runs a bulk import, smaller tenants see 429 errors even though they are well under any reasonable quota. Support logged 41 tickets about this in the last quarter.

This document proposes replacing the global limit with per-tenant limits, enforced at the gateway, with a small shared burst pool.

## Goals

- Isolate tenants from each other so one tenant's traffic spike cannot starve the rest.
- Let us sell higher limits as part of the Enterprise plan.
- Keep added latency under 2 ms at the 99th percentile.
- Roll out without any client-side changes.

## Non-goals

- Limiting by individual API key within a tenant. We may add this later.
- Changing the limits for internal service-to-service traffic.

## Proposed design

### Token bucket per tenant

Each tenant gets a token bucket with two parameters: a refill rate and a burst capacity. Every request takes one token. When the bucket is empty, the gateway returns 429 with a `Retry-After` header.

Default plan values:

| Plan | Refill rate (req/s) | Burst capacity |
| --- | --- | --- |
| Free | 10 | 50 |
| Team | 100 | 500 |
| Enterprise | 1,000 | 5,000 |

### Where the counters live

Bucket state is kept in the existing Redis cluster, one key per tenant. The gateway runs the check as a single Lua script so the read and the decrement happen atomically.

```lua
local tokens = tonumber(redis.call("GET", KEYS[1]) or ARGV[2])
if tokens < 1 then
  return 0
end
redis.call("DECR", KEYS[1])
return 1
```

> Note: the script above does not handle refill yet. Refill will be computed lazily from the last-seen timestamp, stored in a second key.

### Failure behaviour

If Redis is unreachable, the gateway fails open and allows the request. We chose this because a Redis outage should not take down the whole API. The risk is that during an outage no tenant is limited at all.

1. The gateway logs a warning on the first failure.
2. After 30 seconds of failures it pages the on-call engineer.
3. Requests keep flowing until Redis recovers.

## Rollout plan

1. Ship the limiter in shadow mode: count and log, but never reject.
2. Compare shadow decisions with real traffic for two weeks.
3. Enable enforcement for Free tenants.
4. Enable enforcement for all tenants.

## Open questions

- Should the shared burst pool be per region or global?
- Do we need a manual override so support can raise a tenant's limit during an incident?
  - If yes, who is allowed to change it?
  - Should overrides expire automatically?
- How do we communicate the new limits to existing customers?

## Checklist before approval

- [x] Latency benchmark on staging
- [ ] Security review of the fail-open behaviour
- [ ] Pricing sign-off for Enterprise limits
