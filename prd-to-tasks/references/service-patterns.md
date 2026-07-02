> **Generic example / industry-neutral seed.** Copy to `~/.claude/prd-to-tasks/service-patterns.md` and customize with your project's actual helper function names, cache discipline, MQ topology, and ID generation strategy. This file documents principles, not specific API names — your real internal patterns belong in your local KB.
>
> **通用原则 seed。** 复制到 `~/.claude/prd-to-tasks/service-patterns.md` 后填入项目里实际的 helper 函数名、缓存策略、MQ 拓扑、ID 生成方案。本文件只列原则，不写具体 API — 你的真实内部模式应该放在本地 KB。

---

# Service Patterns · 服务代码模式

A reference for "things every task in this codebase must consider but a PRD won't mention".

记录"本代码库里每个任务都要考虑、但 PRD 不会提的事"。

---

## Why this file exists · 为什么需要这个文件

PRD writers don't know about your codebase's:
- ID generation conventions (auto-increment? Snowflake? UUIDv7? KSUID?)
- Cache invalidation discipline (write-through? double-delete? TTL refresh?)
- MQ topic registration (single registry? multiple slices that must sync?)
- Distributed lock instances (which Redis? which key prefix?)
- Idempotency-key conventions (request-id? domain-id+timestamp?)

These are project-specific patterns. Capture YOUR project's actual conventions in your local copy, then reference them from each Phase 4 task with the `spec-refs` mechanism.

PRD 作者不知道你代码库里的具体约定。本文件让你把这些约定显式化，然后通过 Phase 4 任务的 `spec-refs` 反向引用。

---

## P1: ID Generation · 主键 / 业务 ID 生成

**Principle · 原则**: Use your project's centralized ID generation helper, not database auto-increment, for any cross-service or business-meaningful ID. Auto-increment leaks DB-internal state into business APIs.

**项目实际方案 · Your project's actual choice** (TODO when you copy):
- ID generator: Snowflake / UUIDv7 / KSUID / proprietary helper (replace with your choice)
- Helper function name and import path: `<your-project>` (replace)
- When to apply: Any task that creates a new business entity (orders, refunds, line items, etc.)

**Phase 4 task checklist line**: `- [ ] Use <your-id-helper> to generate the new entity's primary key (no auto-increment)`

---

## P2: Cache Invalidation Discipline · 缓存失效

**Principle · 原则**: If your service uses cache-aside with a Redis (or similar) mirror of DB rows, every write must follow a consistent invalidation discipline. Choices commonly include:
- **Write-through**: write DB then write cache
- **Double-delete**: delete cache, write DB, delete cache again (after delay)
- **TTL refresh**: write DB, let cache TTL handle staleness
- **Cache version bump**: increment a version key, lazy-load fresh on next read

Without a unified discipline, race conditions between concurrent writers produce stale reads.

**项目实际方案 · Your project's actual choice** (TODO):
- Discipline: `<write-through|double-delete|ttl|version-bump>` (pick one)
- Helper / utility: `<your-cache-helper>` (replace)
- When to apply: Any task that writes to a DB row mirrored in cache

**Phase 4 task checklist line**: `- [ ] After DB write, follow <your-cache-discipline> using <your-cache-helper>`

---

## P3: MQ Topic Registration · MQ topic 注册

**Principle · 原则**: If your stack maintains multiple message-broker registries (e.g., internal broker + Kafka, or Pulsar + RocketMQ for cross-region), every new topic must be registered in ALL of them. Forgetting one creates silent message drops.

**项目实际方案 · Your project's actual choice** (TODO):
- Registry files: list all paths (e.g. `internal/mq/registry.go`) where topics are declared
- Topic naming convention: `<domain>.<entity>.<event>` (replace with yours)

**Phase 4 task checklist line**: `- [ ] If introducing a new MQ topic, register in all <N> broker registry files in sync`

---

## P4: Distributed Locks · 分布式锁

**Principle · 原则**: Concurrency-sensitive operations (state machine transitions, financial mutations, inventory decrements) need a distributed lock or other atomicity guarantee. Lock instances, key prefixes, and timeout policies must be consistent across services that share the same logical resource.

**项目实际方案 · Your project's actual choice** (TODO):
- Lock instance(s): which Redis / etcd cluster
- Key prefix convention: `<service>:<resource>:<id>`
- Timeout default: <N>s
- Reentrancy: <yes|no>

**Phase 4 task checklist line**: `- [ ] Acquire <your-lock-helper> with key '<convention>' before <operation>`

---

## P5: Idempotency Keys · 幂等键

**Principle · 原则**: Operations that may be retried (payments, refunds, order creation) need an idempotency mechanism. Idempotency keys are typically derived from a stable upstream identifier (e.g., booking-id, request-id), not server-generated.

**项目实际方案 · Your project's actual choice** (TODO):
- Idempotency key source: <upstream-request-id | domain-id | tuple>
- Storage: <db-unique-constraint | redis-with-ttl | dedupe-table>
- TTL: <N>

**Phase 4 task checklist line**: `- [ ] Use idempotency key from <source>; reject duplicate on conflict`

---

## P6: Shared-contracts / Proto Discipline · 跨服务契约纪律

**Principle · 原则**: Shared schema (proto / shared-models / shared-types) is consumed by multiple services. Modifying an existing field (renaming, changing type, reusing a field number/tag) breaks consumers silently. Only **add** new fields with new numbers/tags; never modify existing ones.

**项目实际方案 · Your project's actual choice** (TODO):
- Shared-contracts repo path: <repo>
- Compatibility tool / linter: <buf / protolock / your-tool>

**Phase 4 task checklist line**: `- [ ] All shared-contract changes are field additions only; existing field numbers/tags unchanged; verified by <your-tool>`

---

## Quick reference · 速查

When breaking down a Phase 4 task, walk through this checklist:

```
□ 创建新业务实体? · Creating new business entity?              → P1
□ 写 DB 行有缓存镜像? · Writing DB row with cache mirror?      → P2
□ 新增 MQ topic? · New MQ topic?                              → P3
□ 状态机转换 / 资金变更 / 库存扣减? · State / money / stock?  → P4
□ 操作可重试? · Operation retryable?                          → P5
□ 改 shared-contract? · Shared contract changes?               → P6
```
