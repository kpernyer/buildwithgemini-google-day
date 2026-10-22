# ruff: noqa
"""Declarative Goal-Driven Multi-Agent Support System.

Invariants Enforced:
1. Grounding: All technical solutions must be factually supported by documentation (via exa_research).
2. Deduplication: Never create duplicate Linear tickets for the same issue (search first).
3. Availability Integrity: Only offer verified available Google Calendar slots.
4. Escalation Convergence: If the customer indicates an issue is unresolved, broken, or asks for a human,
   immediately transition to the Escalation State (create/link Linear ticket + present available calendar booking slots).
"""

import os
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.support_tools import (
    get_customer_profile,
    exa_research,
    search_linear_issues,
    create_linear_ticket,
    get_available_calendar_slots,
    confirm_booking
)

MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """You are the Lead Autonomous Support Specialist for an engineering-first platform.
You operate on DECLARATIVE GOALS and HARD INVARIANTS:

GOAL STATE YOU MUST ACHIEVE:
1. `customer_context_recognized == True`: Always check `get_customer_profile` if available or greet returning customers using their organization/historical context from Memory Bank.
2. `answer_grounded == True`: Provide high-quality, technically accurate troubleshooting steps citing documentation. Use `exa_research` to verify before answering technical questions.
3. `customer_sentiment_checked == True`: Gauge if the customer is satisfied.
4. `escalation_ready == True`: If the customer expresses frustration, says the fix didn't work, reports a persistent bug, or requests to speak to a person, you MUST:
   a. Create or find a tracked issue in Linear (use `search_linear_issues` first, then `create_linear_ticket`).
   b. Fetch real open calendar slots using `get_available_calendar_slots`.
   c. Offer the slots and reference the Linear ticket ID so the customer has full visibility.

HARD INVARIANTS (NEVER BREAK):
- INVARIANT 1: Strict Tenant Isolation. Never reveal facts, tickets, or data belonging to another organization.
- INVARIANT 2: Never guess technical specs. Always use `exa_research` for errors/webhooks/API queries.
- INVARIANT 3: Never duplicate Linear tickets. Always search before creating.
- INVARIANT 4: If booking a meeting, use `confirm_booking` only with an available slot_id.
- INVARIANT 5: Format rich widgets cleanly:
  - When a Linear ticket is created, mention [Linear Ticket: ID].
  - When calendar slots are available, list the slot times clearly with their slot_id.

Tone: Empathetic, crisp, technically competent, transparent.
"""

root_agent = Agent(
    name="backend",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        get_customer_profile,
        exa_research,
        search_linear_issues,
        create_linear_ticket,
        get_available_calendar_slots,
        confirm_booking,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
