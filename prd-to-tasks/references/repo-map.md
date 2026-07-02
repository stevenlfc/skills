> **Generic example seed.** Copy to `~/.claude/prd-to-tasks/repo-map.md` and customize for your stack. This file is read-only seed bundled with the skill; your real codebase mappings should live in your local KB, not in this open-source repo.
>
> **行业通用示例 seed。** 复制到 `~/.claude/prd-to-tasks/repo-map.md` 后按你的技术栈改写。本文件是 skill 仓库自带的只读 seed；你的真实代码库映射应该放在本地 KB，不要进开源仓库。

---

# Repo Map · 代码仓库映射

A reference that translates requirement signals (from a PRD) to candidate affected services and repos.

把 PRD 中的需求信号翻译为候选受影响的服务和仓库。

---

## How to use this file · 如何使用

When you read a PRD in Phase 0 and identify it as e.g. "user wants to apply a discount code at checkout", scan this table to find the candidate affected services. Customize the table for your own org's service names and code layout.

读完 PRD 并识别出需求（例如"用户在结账时使用优惠码"）后，扫描下表找到候选受影响的服务。请按你自己组织的服务命名和代码布局改写。

---

## Generic E-commerce / SaaS Service Map · 通用电商 / SaaS 服务映射

### Front-end Gateway / BFF · 前端聚合层

| 需求信号 · Requirement Signal | 候选服务 · Candidate Service | 典型代码布局 · Typical Layout |
|------------------------------|----------------------------|-----------------------------|
| 用户下单、加购物车、商品详情 · Checkout, add to cart, product detail | `bff-service` (mobile-bff / web-bff) | `cmd/<bff-name>/`, `internal/service/` |
| 用户主页、个人中心 · User home, profile | `bff-service` | `internal/service/user/` |
| 搜索聚合、推荐 · Search aggregation, recommendation | `bff-service` or `search-service` | `internal/service/search/` |

### Order Domain · 订单领域

| 需求信号 · Requirement Signal | 候选服务 · Candidate Service | 典型代码布局 · Typical Layout |
|------------------------------|----------------------------|-----------------------------|
| 订单创建、状态推进 · Order creation, state advance | `order-service` | `internal/service/order/`, state machine |
| 退款、售后 · Refunds, after-sales | `refund-service` (or `order-service` sub-module) | `internal/service/refund/` |
| 钱包、余额、积分 · Wallet, balance, points | `wallet-service` | |

### Promotion · 营销

| 需求信号 · Requirement Signal | 候选服务 · Candidate Service | 典型代码布局 · Typical Layout |
|------------------------------|----------------------------|-----------------------------|
| 优惠券、折扣码 · Coupons, discount codes | `voucher-service` or `promotion-service` | |
| 营销活动、限时折扣 · Campaigns, time-limited discounts | `promotion-service` | |

### Inventory · 库存

| 需求信号 · Requirement Signal | 候选服务 · Candidate Service | 典型代码布局 · Typical Layout |
|------------------------------|----------------------------|-----------------------------|
| 库存扣减、回滚、预占 · Stock decrement, rollback, reserve | `inventory-service` | `internal/service/stock/` |
| 跨仓调拨 · Cross-warehouse transfer | `inventory-service` | |

### Payment · 支付

| 需求信号 · Requirement Signal | 候选服务 · Candidate Service | 典型代码布局 · Typical Layout |
|------------------------------|----------------------------|-----------------------------|
| 支付、收款 · Payment, collection | `payment-service` | |
| 结算、对账 · Settlement, reconciliation | `settlement-service` | |

### Fulfillment · 履约

| 需求信号 · Requirement Signal | 候选服务 · Candidate Service | 典型代码布局 · Typical Layout |
|------------------------------|----------------------------|-----------------------------|
| 履约、资源交付 · Fulfillment, resource delivery | `fulfillment-service` | |
| 物流跟踪 · Logistics tracking | `logistics-service` | |

### Shared Contracts · 跨服务契约

| 需求信号 · Requirement Signal | 候选 · Candidate | 备注 · Notes |
|------------------------------|------------------|--------------|
| 跨服务共享 proto / 数据模型 · Cross-service shared proto / model | `shared-contracts` repo (project-specific) | 修改时严守"只新增 field，不修改已有 field number"原则 · "Add-only fields, never modify existing field numbers" |

---

## Customization Checklist · 改写清单

When you copy this to `~/.claude/prd-to-tasks/repo-map.md`, edit:

1. Replace generic service names (`order-service` etc.) with your org's actual service names
2. Update "典型代码布局" column with your real directory conventions
3. Add rows for domains specific to your business (e.g. `auth-service` if SaaS, `creator-service` if marketplace)
4. Delete rows for domains your business doesn't have

把本文件复制到 `~/.claude/prd-to-tasks/repo-map.md` 后，按以上 4 步改写。
