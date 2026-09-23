---
type: schema
verified: true
tags: [database, schema, canonical]
---

# Database Schema Specification

This document is the canonical specification for the core operational
database schema.

## Tables

### `incidents`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| severity | ENUM(P1,P2,P3,P4) | Severity level, see the [SLA Policy](../policies/sla.md) |
| opened_at | TIMESTAMP | When the incident was created |
| resolved_at | TIMESTAMP | When the incident was resolved |
| sla_breached | BOOLEAN | Whether the [SLA Policy](../policies/sla.md) target was missed |

### `customers`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | TEXT | Customer name |
| tier | ENUM(free,pro,enterprise) | Subscription tier, determines applicable [SLA Policy](../policies/sla.md) targets |

## Notes

SLA breach detection logic reads directly from the `incidents` table and
cross-references the response time commitments defined in the canonical
[SLA Policy](../policies/sla.md) document.
