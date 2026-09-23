---
type: policy
verified: true
tags: [sla, policy, support, canonical]
---

# Service Level Agreement (SLA) Policy

This document is the canonical definition of the company's Service Level
Agreement (SLA) commitments for customer support and system uptime.

## Response Time Commitments

| Severity | First Response | Resolution Target |
|----------|-----------------|--------------------|
| Critical (P1) | 15 minutes | 4 hours |
| High (P2) | 1 hour | 8 hours |
| Medium (P3) | 4 hours | 2 business days |
| Low (P4) | 1 business day | 5 business days |

## Uptime Commitment

The platform guarantees **99.9% uptime** measured monthly, excluding
scheduled maintenance windows communicated at least 48 hours in advance.

## Related Documents

- See the [Database Schema](../schemas/database.md) for how SLA breach
  events are recorded and tracked in the system.

## Escalation

Any SLA breach must be logged and escalated to the on-call engineering
manager within 30 minutes of detection.
