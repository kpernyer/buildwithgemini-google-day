"""Memory Bank & Multi-Tenant Organization Store.

Provides:
- Multi-tenant organizations:
    * org_acme (Acme Corp): Enterprise ERP logistics customer on Google Cloud
    * org_fintech (FinPulse): Strict compliance European bank in Frankfurt & Stockholm
    * org_retail (ShopEase): E-commerce platform scaling up for Black Friday
- Typed, atomic memory extraction with strict tenant isolation (tenant_id:user_id).
- PreloadMemoryTool pattern for ADK.
"""

from typing import Dict, List, Any
import datetime

# Pre-seeded organizations and users with distinct background knowledge
ORGANIZATIONS: Dict[str, Dict[str, Any]] = {
    "org_acme": {
        "name": "Acme Logistics Corp",
        "tier": "Enterprise",
        "stack": "Google Cloud + Kubernetes",
        "users": {
            "kenneth": {
                "name": "Kenneth Pernyer",
                "role": "CTO",
                "email": "kenneth@acme.com",
            },
            "sarah": {
                "name": "Sarah Miller",
                "role": "Lead DevOps",
                "email": "sarah@acme.com",
            }
        }
    },
    "org_fintech": {
        "name": "FinPulse Banking",
        "tier": "Mission-Critical Bank",
        "stack": "On-prem + GCP Stockholm (europe-north1)",
        "users": {
            "erik": {
                "name": "Erik Lindqvist",
                "role": "Chief Security Officer",
                "email": "erik@finpulse.se",
            }
        }
    },
    "org_retail": {
        "name": "ShopEase Global",
        "tier": "Growth",
        "stack": "Node.js + Cloud Run",
        "users": {
            "maya": {
                "name": "Maya Patel",
                "role": "Head of Engineering",
                "email": "maya@shopease.io",
            }
        }
    }
}

# The Multi-Tenant Memory Bank store (keyed strictly by tenant_id:user_id)
MEMORY_BANK_DB: Dict[str, List[Dict[str, Any]]] = {
    "org_acme:kenneth": [
        {
            "fact": "Company runs mission-critical ERP webhook sync that processes >10k events/min.",
            "category": "architecture",
            "last_updated": "2026-09-15"
        },
        {
            "fact": "Experienced payload timeout issues on 5MB payloads in past sprint; team uses gzip compression.",
            "category": "incident_history",
            "last_updated": "2026-10-01"
        },
        {
            "fact": "Kenneth prefers direct technical explanations and immediate calendar booking escalation over chatbot fluff.",
            "category": "communication_preference",
            "last_updated": "2026-10-10"
        }
    ],
    "org_fintech:erik": [
        {
            "fact": "Strict compliance mandate: Zero data can leave EU/Stockholm region (europe-north1).",
            "category": "compliance",
            "last_updated": "2026-08-20"
        },
        {
            "fact": "Requires signed DPA before testing any preview features.",
            "category": "legal",
            "last_updated": "2026-09-02"
        }
    ],
    "org_retail:maya": [
        {
            "fact": "Currently prepping infrastructure for Black Friday flash traffic (10x normal load).",
            "category": "business_context",
            "last_updated": "2026-10-18"
        },
        {
            "fact": "Tech stack runs on Node.js and TypeScript on Cloud Run.",
            "category": "tech_stack",
            "last_updated": "2026-10-18"
        }
    ]
}


def get_tenant_memories(tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
    """Retrieves memories strictly partitioned by tenant_id:user_id.
    Hard Invariant: NEVER returns data from another tenant.
    """
    key = f"{tenant_id}:{user_id}"
    return MEMORY_BANK_DB.get(key, [])


def save_tenant_memory(tenant_id: str, user_id: str, fact: str, category: str = "general") -> None:
    """Consolidates a new fact into the tenant's memory partition."""
    key = f"{tenant_id}:{user_id}"
    if key not in MEMORY_BANK_DB:
        MEMORY_BANK_DB[key] = []
    MEMORY_BANK_DB[key].append({
        "fact": fact,
        "category": category,
        "last_updated": datetime.date.today().isoformat()
    })
