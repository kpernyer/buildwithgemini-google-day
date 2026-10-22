# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
from collections.abc import AsyncIterator

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.genai import types

load_dotenv()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "true"

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.reasoning_engine_adapter import (
    attach_reasoning_engine_routes,
)

load_dotenv()
allow_origins = ["*"]
otel_to_cloud = os.environ.get(
    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", ""
).lower() in ("true", "1")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=otel_to_cloud,
    lifespan=lifespan,
)
app.title = "backend"
app.description = "API for interacting with the Agent backend"

# Proxy routes so the Google Cloud console playground (reasoning_engine SDK) can
# talk to this agent alongside the native adk_api routes.
attach_reasoning_engine_routes(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default-session"
    user_id: str = "kenneth"
    tenant_id: str = "org_acme"

class BookingRequest(BaseModel):
    slot_id: str
    customer_name: str
    customer_email: str
    issue_summary: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    runner: Runner = app.state.runner
    adk_app_name = app.state.agent_app_name
    session_service = runner.session_service
    
    # Scoped composite user key ensuring tenant boundary
    scoped_user_id = f"{req.tenant_id}:{req.user_id}"
    
    # Ensure session exists
    session = await session_service.get_session(app_name=adk_app_name, user_id=scoped_user_id, session_id=req.session_id)
    if not session:
        session = await session_service.create_session(app_name=adk_app_name, user_id=scoped_user_id, session_id=req.session_id)
        
    user_content = types.Content(role="user", parts=[types.Part.from_text(
        text=f"[Context: tenant_id='{req.tenant_id}', user_id='{req.user_id}']\n{req.message}"
    )])
    
    response_text = ""
    tools_called = []
    
    async for event in runner.run_async(user_id=req.user_id, session_id=session.id, new_message=user_content):
        if event.content and event.content.parts:
            for p in event.content.parts:
                if p.text:
                    response_text += p.text
                if hasattr(p, "function_call") and p.function_call:
                    tools_called.append(p.function_call.name)

    # Inspect current state
    from app.support_tools import LINEAR_ISSUES_DB, BOOKINGS_DB
    
    return {
        "reply": response_text,
        "tools_called": tools_called,
        "session_id": session.id,
        "linear_tickets": LINEAR_ISSUES_DB,
        "bookings": BOOKINGS_DB
    }

@app.get("/api/state")
async def state_endpoint(tenant_id: str = "org_acme", user_id: str = "kenneth"):
    from app.support_tools import LINEAR_ISSUES_DB, BOOKINGS_DB, get_available_calendar_slots
    from app.memory_store import ORGANIZATIONS, get_tenant_memories
    import json
    slots_data = json.loads(get_available_calendar_slots())
    memories = get_tenant_memories(tenant_id, user_id)
    return {
        "organizations": ORGANIZATIONS,
        "current_tenant": tenant_id,
        "current_user": user_id,
        "memories": memories,
        "linear_tickets": LINEAR_ISSUES_DB,
        "bookings": BOOKINGS_DB,
        "available_slots": slots_data.get("slots", [])
    }

@app.post("/api/book")
async def book_endpoint(req: BookingRequest):
    from app.support_tools import confirm_booking
    import json
    result = confirm_booking(
        slot_id=req.slot_id,
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        issue_summary=req.issue_summary
    )
    return json.loads(result)



# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
