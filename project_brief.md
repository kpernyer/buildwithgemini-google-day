# My agent: Nexus Ops — Declarative Goal-Driven Support Agent

One-liner: A declarative, goal-driven autonomous support agent powered by Google ADK and multi-tenant Memory Bank that verifies documentation, deduplicates Linear issues, and books conflict-free Google Calendar deep-dives.

## Architecture & Invariants

Instead of brittle decision trees, Nexus Ops operates on **desired states (goals)** and **hard invariants**:
- **Multi-Tenant Memory Isolation**: Scoped by `tenant_id:user_id` (`org_acme:kenneth`, `org_fintech:erik`, `org_retail:maya`).
- **Grounded Troubleshooting**: Verifies technical documentation via `exa_research` before answering.
- **Zero Duplicate Tickets**: Searches Linear (`search_linear_issues`) before creating new engineering escalations (`create_linear_ticket`).
- **Conflict-Free Scheduling**: Offers verified open Google Calendar slots (`get_available_calendar_slots`) and confirms holds (`confirm_booking`).
