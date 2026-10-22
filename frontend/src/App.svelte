<script lang="ts">
  import { onMount } from "svelte";

  // Top level mode:
  // 'customer_portal' = The Mock SaaS business app ("Nexus Cloud") with Intercom launcher & org switcher
  // 'control_plane' = The Macaly-style Goal Builder where the founder describes scenarios & sees them live
  let activeMode: "customer_portal" | "control_plane" = "customer_portal";

  // Customer Intercom Drawer state
  let isIntercomOpen = false;

  interface Message {
    id: string;
    sender: "user" | "agent" | "system";
    text: string;
    timestamp: string;
    tools?: string[];
    isCard?: boolean;
    cardType?: "slots" | "linear" | "booking_confirmed";
    data?: any;
  }

  interface Slot {
    slot_id: string;
    date: string;
    time: string;
    available: boolean;
  }

  interface LinearTicket {
    id: string;
    title: string;
    priority: string;
    status: string;
  }

  interface MemoryItem {
    fact: string;
    category: string;
    last_updated: string;
  }

  const TENANTS = [
    {
      tenant_id: "org_acme",
      user_id: "kenneth",
      label: "Kenneth Pernyer",
      company: "Acme Logistics Corp",
      role: "CTO",
      badge: "Enterprise ERP",
      avatarBg: "#FFD09B",
      activeIncident: "Webhook ERP Sync throwing 500 errors on 5.2MB payloads (14:22 CET)",
    },
    {
      tenant_id: "org_fintech",
      user_id: "erik",
      label: "Erik Lindqvist",
      company: "FinPulse Banking",
      role: "Chief Security Officer",
      badge: "EU Sovereign",
      avatarBg: "#D3BFFF",
      activeIncident: "Compliance gate blocking preview testing outside europe-north1",
    },
    {
      tenant_id: "org_retail",
      user_id: "maya",
      label: "Maya Patel",
      company: "ShopEase Global",
      role: "Head of Engineering",
      badge: "10x Peak Load",
      avatarBg: "#FFC6EE",
      activeIncident: "Traffic scaling alert: 8x surge detected on checkout API",
    },
  ];

  let activeTenant = TENANTS[0];
  let activeMemories: MemoryItem[] = [];
  let activeLinearTickets: LinearTicket[] = [];
  let availableSlots: Slot[] = [];
  let selectedSlot: Slot | null = null;
  let isBooking = false;
  let inputMessage = "";
  let isLoading = false;
  let chatBox: HTMLDivElement;

  // Control Plane Scenarios State ("Tell What Needs to Be True")
  let scenarios = [
    {
      id: "sc-1",
      title: "Enterprise Webhook 500 Escalation",
      prompt:
        "When an Enterprise customer hits persistent webhook 500 errors after trying compression, do not make them wait. Check Linear to prevent duplicates, open a High priority bug, and pull live Google Calendar slots to offer a 15-minute engineer call.",
      goals: ["answer_grounded", "no_duplicate_tickets", "escalation_ready"],
      active: true,
      appliedAt: "Active on runtime",
    },
    {
      id: "sc-2",
      title: "EU Sovereign Data Compliance Guardrail",
      prompt:
        "If a financial institution asks to test preview AI features, strictly enforce the signed DPA rule and verify that no data leaves europe-north1 before providing documentation.",
      goals: ["strict_eu_compliance", "dpa_verified"],
      active: true,
      appliedAt: "Active on runtime",
    },
  ];

  let newScenarioPrompt = "";
  let isSynthesizingScenario = false;

  let messages: Message[] = [];

  function resetChatForTenant() {
    messages = [
      {
        id: "m-intro",
        sender: "agent",
        text: `Hey ${activeTenant.label}! Connected to your ${activeTenant.company} environment. How can we help you right now?`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ];
    fetchState();
  }

  async function fetchState() {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/api/state?tenant_id=${activeTenant.tenant_id}&user_id=${activeTenant.user_id}`
      );
      const data = await res.json();
      activeMemories = data.memories || [];
      activeLinearTickets = data.linear_tickets || [];
      availableSlots = data.available_slots || [];
    } catch (e) {
      console.error("State fetch error:", e);
    }
  }

  onMount(() => {
    resetChatForTenant();
  });

  function selectTenant(tenant: typeof TENANTS[0]) {
    activeTenant = tenant;
    resetChatForTenant();
  }

  function scrollToBottom() {
    setTimeout(() => {
      if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
    }, 50);
  }

  async function sendMessage(textToSend?: string) {
    const text = textToSend || inputMessage;
    if (!text.trim() || isLoading) return;

    if (!isIntercomOpen) isIntercomOpen = true;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    messages = [...messages, userMsg];
    inputMessage = "";
    isLoading = true;
    scrollToBottom();

    try {
      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: `session-${activeTenant.tenant_id}`,
          user_id: activeTenant.user_id,
          tenant_id: activeTenant.tenant_id,
        }),
      });

      const data = await res.json();

      const agentMsg: Message = {
        id: `a-${Date.now()}`,
        sender: "agent",
        text: data.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        tools: data.tools_called || [],
      };

      messages = [...messages, agentMsg];
      activeLinearTickets = data.linear_tickets || [];

      if (data.tools_called?.includes("get_available_calendar_slots")) {
        await fetchState();
        if (availableSlots.length > 0) {
          messages = [
            ...messages,
            {
              id: `slot-${Date.now()}`,
              sender: "system",
              text: "Engineering Escalation: Available Booking Slots",
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              isCard: true,
              cardType: "slots",
              data: availableSlots,
            },
          ];
        }
      }
    } catch (e) {
      messages = [
        ...messages,
        {
          id: `err-${Date.now()}`,
          sender: "system",
          text: "Connection to agent engine interrupted. Please retry.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ];
    } finally {
      isLoading = false;
      scrollToBottom();
    }
  }

  async function handleConfirmBooking() {
    if (!selectedSlot) return;
    isBooking = true;

    try {
      const res = await fetch("http://127.0.0.1:8000/api/book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slot_id: selectedSlot.slot_id,
          customer_name: `${activeTenant.label} (${activeTenant.company})`,
          customer_email: `${activeTenant.user_id}@example.com`,
          issue_summary: `Escalation from ${activeTenant.company}`,
        }),
      });

      const data = await res.json();
      if (data.status === "confirmed") {
        messages = [
          ...messages,
          {
            id: `conf-${Date.now()}`,
            sender: "system",
            text: `Meeting confirmed with Lead Support Engineer. Calendar hold placed.`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            isCard: true,
            cardType: "booking_confirmed",
            data: data.booking,
          },
        ];
        selectedSlot = null;
        await fetchState();
      }
    } catch (e) {
      alert("Booking failed. Please try again.");
    } finally {
      isBooking = false;
      scrollToBottom();
    }
  }

  function handleCreateScenario() {
    if (!newScenarioPrompt.trim()) return;
    isSynthesizingScenario = true;

    setTimeout(() => {
      scenarios = [
        {
          id: `sc-${Date.now()}`,
          title: "Custom Declared Scenario",
          prompt: newScenarioPrompt,
          goals: ["custom_invariant_enforced", "adk_auto_wired"],
          active: true,
          appliedAt: "Just compiled to ADK",
        },
        ...scenarios,
      ];
      newScenarioPrompt = "";
      isSynthesizingScenario = false;
    }, 600);
  }
</script>

<div class="app-root">
  <!-- Top Navigation Pill (Macaly Floating Glass) -->
  <header class="top-nav-bar">
    <div class="nav-pill">
      <!-- Brand -->
      <div class="brand-group">
        <span class="brand-tag">✦ Nexus Ops</span>
      </div>

      <!-- Mode Switcher -->
      <div class="view-segmented-control">
        <button
          class="seg-btn {activeMode === 'customer_portal' ? 'active' : ''}"
          on:click={() => (activeMode = "customer_portal")}
        >
          1. Customer App (Nexus Cloud + Intercom)
        </button>
        <button
          class="seg-btn {activeMode === 'control_plane' ? 'active' : ''}"
          on:click={() => (activeMode = "control_plane")}
        >
          2. Founder Control Plane (Tell What Needs to Be True)
        </button>
      </div>

      <!-- Live Engine Indicator -->
      <div class="runtime-badge">
        <span class="live-dot"></span>
        Google ADK Live
      </div>
    </div>
  </header>

  <!-- ========================================================================= -->
  <!-- SURFACE 1: THE MOCK BUSINESS ("Nexus Cloud Platform" with Intercom Drawer) -->
  <!-- ========================================================================= -->
  {#if activeMode === "customer_portal"}
    <div class="nexus-app-container">
      <!-- Nexus Top Bar -->
      <div class="nexus-topbar">
        <div class="nexus-logo">
          <span class="nexus-cube">■</span>
          <span class="nexus-title">NEXUS CLOUD PLATFORM</span>
        </div>

        <!-- Org Switcher Dropdown in App Header -->
        <div class="user-org-switcher">
          <span class="org-label">Logged in as:</span>
          <div class="org-chips">
            {#each TENANTS as tenant}
              <button
                class="org-chip {activeTenant.tenant_id === tenant.tenant_id ? 'active' : ''}"
                on:click={() => selectTenant(tenant)}
              >
                <span class="avatar-dot" style="background: {tenant.avatarBg};"></span>
                <strong>{tenant.label}</strong> ({tenant.company})
              </button>
            {/each}
          </div>
        </div>
      </div>

      <!-- Nexus Main Workspace (Mocked Real Product Dashboard) -->
      <main class="nexus-main-workspace">
        <div class="workspace-header">
          <div>
            <span class="subtle-kicker">Environment: Production (Europe)</span>
            <h1 class="workspace-h1">Webhook & API Event Streams</h1>
            <p class="workspace-desc">Real-time inspection of active customer ingestion pipelines.</p>
          </div>

          <!-- Quick Action to Trigger Real Support Issue -->
          <div class="trouble-alert-box">
            <div class="alert-icon">⚠️</div>
            <div class="alert-content">
              <strong>Active Pipeline Alert for {activeTenant.company}:</strong>
              <p>{activeTenant.activeIncident}</p>
            </div>
            <button
              class="ask-support-btn"
              on:click={() => {
                isIntercomOpen = true;
                sendMessage(
                  `We are seeing repeated failures on our ${activeTenant.company} pipeline. ${activeTenant.activeIncident}. Can you check this?`
                );
              }}
            >
              Ask Support (Intercom) ↗
            </button>
          </div>
        </div>

        <!-- Live Feed Table -->
        <div class="nexus-card feed-card">
          <div class="feed-header">
            <h3>Recent Ingestion Events</h3>
            <span class="feed-status">Live Polling</span>
          </div>

          <table class="event-table">
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Target Endpoint</th>
                <th>Payload Size</th>
                <th>Status</th>
                <th>Timestamp</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr class="error-row">
                <td><code>evt_9921_erp</code></td>
                <td><code>/api/v2/webhooks/erp-sync</code></td>
                <td><strong>5.2 MB</strong> (Exceeds 5MB standard)</td>
                <td><span class="status-badge error">500 Server Error</span></td>
                <td>14:22:10 CET</td>
                <td>
                  <button
                    class="table-support-link"
                    on:click={() => {
                      isIntercomOpen = true;
                      sendMessage("We tried gzip compression but payloads are still failing with 500s. We need someone to jump on a call.");
                    }}
                  >
                    Report to Support
                  </button>
                </td>
              </tr>
              <tr>
                <td><code>evt_9920_auth</code></td>
                <td><code>/api/v2/auth/token</code></td>
                <td>0.8 KB</td>
                <td><span class="status-badge success">200 OK</span></td>
                <td>14:20:05 CET</td>
                <td>—</td>
              </tr>
              <tr>
                <td><code>evt_9919_orders</code></td>
                <td><code>/api/v2/orders/stream</code></td>
                <td>42.1 KB</td>
                <td><span class="status-badge success">200 OK</span></td>
                <td>14:18:44 CET</td>
                <td>—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>

      <!-- Floating Intercom Launcher Button (Bottom Right) -->
      <div class="intercom-fab-container">
        {#if !isIntercomOpen}
          <button class="intercom-fab" on:click={() => (isIntercomOpen = true)}>
            <span class="intercom-icon">💬</span>
            <span class="intercom-fab-label">Chat with Support</span>
          </button>
        {/if}
      </div>

      <!-- Intercom Floating Drawer Widget -->
      {#if isIntercomOpen}
        <aside class="intercom-widget-drawer">
          <header class="intercom-drawer-header">
            <div class="intercom-header-info">
              <div class="agent-avatar-circle">✦</div>
              <div>
                <h4>Nexus Autonomous Support</h4>
                <p>Powered by Google ADK & Vertex AI Memory Bank</p>
              </div>
            </div>
            <button class="close-drawer-btn" on:click={() => (isIntercomOpen = false)}>✕</button>
          </header>

          <!-- Drawer Body -->
          <div class="intercom-drawer-messages" bind:this={chatBox}>
            {#each messages as msg}
              <div class="intercom-message-row {msg.sender}">
                <div class="intercom-bubble {msg.sender}">
                  <p class="bubble-text">{msg.text}</p>

                  {#if msg.tools && msg.tools.length > 0}
                    <div class="drawer-tool-pills">
                      <span class="drawer-tool-label">Tools:</span>
                      {#each msg.tools as tool}
                        <span class="drawer-tool-pill">⚙ {tool}</span>
                      {/each}
                    </div>
                  {/if}

                  <!-- Inline Booking Hold Card -->
                  {#if msg.isCard && msg.cardType === "slots"}
                    <div class="drawer-card booking-hold">
                      <div class="booking-header">
                        <span class="calendar-emoji">📅</span>
                        <div>
                          <strong>Technical Escalation Hold</strong>
                          <p>Direct 1:1 with Lead Support Engineer:</p>
                        </div>
                      </div>

                      <div class="drawer-slot-grid">
                        {#each availableSlots as slot}
                          <button
                            class="drawer-slot-btn {selectedSlot?.slot_id === slot.slot_id ? 'active' : ''}"
                            on:click={() => (selectedSlot = slot)}
                          >
                            <span class="slot-time">{slot.time}</span>
                            <span class="slot-date">{slot.date}</span>
                          </button>
                        {/each}
                      </div>

                      {#if selectedSlot}
                        <div class="booking-confirm-footer">
                          <span>Selected: {selectedSlot.time}</span>
                          <button
                            class="drawer-confirm-btn"
                            disabled={isBooking}
                            on:click={handleConfirmBooking}
                          >
                            {isBooking ? "Booking..." : "Confirm Google Meet"}
                          </button>
                        </div>
                      {/if}
                    </div>
                  {/if}

                  <!-- Booking Confirmed Card -->
                  {#if msg.isCard && msg.cardType === "booking_confirmed"}
                    <div class="drawer-card confirmed-hold">
                      <strong>✓ Google Meet Confirmed</strong>
                      <p>Meeting booked for slot {msg.data.slot_id}.</p>
                      <a href={msg.data.meet_link} target="_blank" class="drawer-meet-link">
                        {msg.data.meet_link} ↗
                      </a>
                    </div>
                  {/if}

                  <span class="drawer-time">{msg.timestamp}</span>
                </div>
              </div>
            {/each}

            {#if isLoading}
              <div class="intercom-message-row agent">
                <div class="intercom-bubble agent loading">
                  <span>●</span><span>●</span><span>●</span>
                </div>
              </div>
            {/if}
          </div>

          <!-- Drawer Composer -->
          <footer class="intercom-drawer-composer">
            <input
              type="text"
              class="drawer-input"
              placeholder={`Message support as ${activeTenant.label}...`}
              bind:value={inputMessage}
              on:keydown={(e) => e.key === "Enter" && sendMessage()}
            />
            <button
              class="drawer-send-btn"
              disabled={isLoading || !inputMessage.trim()}
              on:click={() => sendMessage()}
            >
              Send
            </button>
          </footer>
        </aside>
      {/if}
    </div>
  {:else}
    <!-- ========================================================================= -->
    <!-- SURFACE 2: THE FOUNDER CONTROL PLANE ("Tell What Needs to Be True")       -->
    <!-- ========================================================================= -->
    <div class="control-plane-container">
      <div class="control-hero">
        <span class="hero-sticker">GOAL-DRIVEN CONTROL PLANE</span>
        <h1 class="macaly-serif-title">
          Tell what needs to be true.<br />
          <span>The agent orchestrates the rest.</span>
        </h1>
        <p class="macaly-hero-sub">
          Instead of building rigid decision trees, describe scenarios in plain English. The compiler turns your policy into
          ADK goals, invariants, and automated tool bindings.
        </p>
      </div>

      <!-- The Scenario Composer (Macaly Signature Input Box) -->
      <section class="scenario-composer-card">
        <div class="composer-header">
          <span class="composer-tag">✨ Scenario Synthesizer</span>
          <h3>Describe a New Support Policy or Invariant</h3>
        </div>

        <textarea
          class="macaly-scenario-textarea"
          rows="3"
          placeholder="e.g. When a customer reports payload errors exceeding 5MB, verify their past tickets in Linear. If unresolved after 2 turns, place a tentative hold on Google Calendar and ping Slack."
          bind:value={newScenarioPrompt}
        ></textarea>

        <div class="composer-footer">
          <div class="composer-helpers">
            <span class="helper-pill">Target: Zero Hallucination</span>
            <span class="helper-pill">Auto-Binds: Exa + Linear + Memory Bank</span>
          </div>
          <button
            class="macaly-btn-black"
            disabled={isSynthesizingScenario || !newScenarioPrompt.trim()}
            on:click={handleCreateScenario}
          >
            {isSynthesizingScenario ? "Compiling Invariants..." : "Compile into ADK Invariants →"}
          </button>
        </div>
      </section>

      <!-- Active Scenarios & Enforced Invariants -->
      <section class="active-scenarios-section">
        <div class="section-title-row">
          <h2>Active Compiled Scenarios ({scenarios.length})</h2>
          <span class="badge-tag">Enforced by Verifier Loop</span>
        </div>

        <div class="scenarios-grid">
          {#each scenarios as sc}
            <div class="scenario-card">
              <div class="sc-top">
                <h4>{sc.title}</h4>
                <span class="status-pill active">LIVE</span>
              </div>
              <p class="sc-prompt">"{sc.prompt}"</p>
              <div class="sc-goals-tray">
                {#each sc.goals as goal}
                  <span class="sc-goal-chip">✓ {goal}</span>
                {/each}
              </div>
              <div class="sc-footer">
                <span class="sc-runtime">{sc.appliedAt}</span>
              </div>
            </div>
          {/each}
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..600;1,9..144,300..600&family=Inter:wght@400;500;600;700&display=swap");

  :global(body) {
    margin: 0;
    padding: 0;
    background-color: #f7fbcf;
    color: #1f1f1f;
    font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  }

  .app-root {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background: #f7fbcf;
  }

  /* Top Navigation */
  .top-nav-bar {
    position: sticky;
    top: 0;
    z-index: 50;
    display: flex;
    justify-content: center;
    padding: 14px 24px;
    background: linear-gradient(to bottom, rgba(247, 251, 207, 0.95), rgba(247, 251, 207, 0));
    backdrop-filter: blur(8px);
  }

  .nav-pill {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    max-width: 1100px;
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(24px) saturate(1.8);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-radius: 20px;
    padding: 8px 16px;
    box-shadow: 0 10px 30px -16px rgba(0, 0, 0, 0.15);
  }

  .brand-tag {
    font-size: 0.82rem;
    font-weight: 700;
    background: #000;
    color: #fff;
    padding: 6px 12px;
    border-radius: 12px;
  }

  .view-segmented-control {
    display: flex;
    background: rgba(0, 0, 0, 0.06);
    padding: 4px;
    border-radius: 14px;
    gap: 4px;
  }

  .seg-btn {
    background: transparent;
    border: none;
    font-size: 0.82rem;
    font-weight: 600;
    color: #555;
    padding: 6px 16px;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .seg-btn.active {
    background: #fff;
    color: #000;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  }

  .runtime-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #fff;
    border: 1px solid rgba(0, 0, 0, 0.1);
    padding: 5px 12px;
    border-radius: 12px;
  }

  .live-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 8px #22c55e;
  }

  /* SURFACE 1: Mock SaaS App ("Nexus Cloud") */
  .nexus-app-container {
    flex: 1;
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    padding: 16px 24px 60px 24px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 20px;
    position: relative;
  }

  .nexus-topbar {
    background: #ffffff;
    border: 1px solid #000000;
    border-radius: 14px;
    padding: 14px 20px;
    box-shadow: 2px 2px 0 0 #000000;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .nexus-logo {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .nexus-cube {
    font-size: 1.2rem;
    color: #000;
  }

  .nexus-title {
    font-weight: 800;
    font-size: 0.95rem;
    letter-spacing: 0.05em;
  }

  .user-org-switcher {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .org-label {
    font-size: 0.75rem;
    color: #666;
  }

  .org-chips {
    display: flex;
    gap: 6px;
  }

  .org-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #f7f7f7;
    border: 1px solid #000;
    padding: 5px 10px;
    border-radius: 8px;
    font-size: 0.78rem;
    cursor: pointer;
    box-shadow: 1px 1px 0 #000;
    transition: all 0.15s;
  }

  .org-chip.active {
    background: #ffd09b;
    box-shadow: 2px 2px 0 #000;
  }

  .avatar-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 1px solid #000;
  }

  .nexus-main-workspace {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .workspace-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
  }

  .subtle-kicker {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #666;
    letter-spacing: 0.05em;
  }

  .workspace-h1 {
    font-family: "Fraunces", Georgia, serif;
    font-size: 2.2rem;
    font-weight: 500;
    margin: 4px 0 6px 0;
  }

  .workspace-desc {
    margin: 0;
    font-size: 0.9rem;
    color: #555;
  }

  .trouble-alert-box {
    background: #ffffff;
    border: 1px solid #000000;
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 2px 2px 0 0 #000000;
    display: flex;
    align-items: center;
    gap: 14px;
    max-width: 460px;
  }

  .alert-icon {
    font-size: 1.6rem;
  }

  .alert-content strong {
    display: block;
    font-size: 0.82rem;
    color: #dc2626;
  }

  .alert-content p {
    margin: 2px 0 0 0;
    font-size: 0.76rem;
    color: #444;
  }

  .ask-support-btn {
    background: #000;
    color: #fff;
    border: 1px solid #000;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    box-shadow: 1px 1px 0 #000;
  }

  .nexus-card {
    background: #ffffff;
    border: 1px solid #000000;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 2px 2px 0 0 #000000;
  }

  .feed-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .feed-header h3 {
    margin: 0;
    font-size: 1.1rem;
  }

  .feed-status {
    font-size: 0.72rem;
    font-weight: 700;
    background: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
    padding: 3px 8px;
    border-radius: 10px;
  }

  .event-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  .event-table th {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid #000;
    font-size: 0.75rem;
    text-transform: uppercase;
    color: #555;
  }

  .event-table td {
    padding: 12px;
    border-bottom: 1px solid #eee;
  }

  .error-row {
    background: #fff5f5;
  }

  .status-badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid #000;
  }

  .status-badge.error {
    background: #fee2e2;
    color: #991b1b;
  }

  .status-badge.success {
    background: #dcfce7;
    color: #166534;
  }

  .table-support-link {
    background: transparent;
    border: 1px solid #000;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 1px 1px 0 #000;
  }

  /* Floating Intercom Launcher */
  .intercom-fab-container {
    position: fixed;
    bottom: 24px;
    right: 32px;
    z-index: 100;
  }

  .intercom-fab {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #000000;
    color: #ffffff;
    border: 1px solid #000000;
    border-radius: 30px;
    padding: 12px 20px;
    font-size: 0.9rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 3px 3px 0 0 #ffd09b;
    transition: transform 0.15s;
  }

  .intercom-fab:hover {
    transform: translateY(-2px);
  }

  /* Intercom Drawer (Floating right) */
  .intercom-widget-drawer {
    position: fixed;
    bottom: 24px;
    right: 32px;
    width: 420px;
    height: 640px;
    background: #ffffff;
    border: 1px solid #000000;
    border-radius: 16px;
    box-shadow: 4px 4px 0 0 #000000;
    display: flex;
    flex-direction: column;
    z-index: 101;
    overflow: hidden;
  }

  .intercom-drawer-header {
    background: #ffd09b;
    border-bottom: 1px solid #000000;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .intercom-header-info {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .agent-avatar-circle {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #000;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
  }

  .intercom-header-info h4 {
    margin: 0;
    font-size: 0.88rem;
    color: #000;
  }

  .intercom-header-info p {
    margin: 2px 0 0 0;
    font-size: 0.68rem;
    color: #333;
  }

  .close-drawer-btn {
    background: transparent;
    border: 1px solid #000;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    cursor: pointer;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .intercom-drawer-messages {
    flex: 1;
    overflow-y: auto;
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: #fafafa;
  }

  .intercom-message-row {
    display: flex;
    width: 100%;
  }

  .intercom-message-row.user {
    justify-content: flex-end;
  }

  .intercom-bubble {
    max-width: 82%;
    padding: 12px 14px;
    border-radius: 12px;
    font-size: 0.85rem;
    line-height: 1.45;
    border: 1px solid #000;
  }

  .intercom-bubble.user {
    background: #000;
    color: #fff;
    box-shadow: 2px 2px 0 #ffd09b;
  }

  .intercom-bubble.agent {
    background: #fff;
    color: #111;
    box-shadow: 2px 2px 0 #000;
  }

  .intercom-bubble.system {
    background: #ffd09b;
    color: #000;
    width: 90%;
  }

  .drawer-tool-pills {
    margin-top: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .drawer-tool-label {
    font-size: 0.65rem;
    font-weight: 700;
    color: #555;
  }

  .drawer-tool-pill {
    font-size: 0.65rem;
    background: #fff;
    border: 1px solid #000;
    padding: 1px 6px;
    border-radius: 6px;
  }

  .drawer-card {
    margin-top: 10px;
    background: #fff;
    border: 1px solid #000;
    border-radius: 8px;
    padding: 10px;
  }

  .booking-header {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }

  .drawer-slot-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
  }

  .drawer-slot-btn {
    background: #fafafa;
    border: 1px solid #000;
    border-radius: 6px;
    padding: 6px;
    font-size: 0.72rem;
    cursor: pointer;
  }

  .drawer-slot-btn.active {
    background: #000;
    color: #fff;
  }

  .booking-confirm-footer {
    margin-top: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
  }

  .drawer-confirm-btn {
    background: #000;
    color: #fff;
    border: 1px solid #000;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
  }

  .drawer-meet-link {
    display: inline-block;
    margin-top: 4px;
    font-weight: 700;
    color: #166534;
    text-decoration: underline;
    font-size: 0.75rem;
  }

  .drawer-time {
    display: block;
    margin-top: 4px;
    font-size: 0.65rem;
    opacity: 0.6;
    text-align: right;
  }

  .intercom-drawer-composer {
    display: flex;
    padding: 10px 14px;
    background: #fff;
    border-top: 1px solid #000;
    gap: 8px;
  }

  .drawer-input {
    flex: 1;
    border: 1px solid #000;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.85rem;
    outline: none;
  }

  .drawer-send-btn {
    background: #000;
    color: #fff;
    border: 1px solid #000;
    border-radius: 8px;
    padding: 0 14px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
  }

  /* SURFACE 2: Founder Control Plane */
  .control-plane-container {
    max-width: 1100px;
    width: 100%;
    margin: 0 auto;
    padding: 20px 24px 60px 24px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  .control-hero {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .hero-sticker {
    align-self: flex-start;
    font-size: 0.72rem;
    font-weight: 800;
    background: #ffd09b;
    border: 1px solid #000;
    padding: 3px 10px;
    border-radius: 6px;
    box-shadow: 1px 1px 0 #000;
  }

  .macaly-serif-title {
    font-family: "Fraunces", Georgia, serif;
    font-size: 3rem;
    font-weight: 500;
    line-height: 1.05;
    margin: 0;
  }

  .macaly-hero-sub {
    font-size: 1.05rem;
    color: #444;
    max-width: 720px;
    margin: 0;
  }

  /* Scenario Composer Card */
  .scenario-composer-card {
    background: #ffffff;
    border: 1px solid #000000;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 3px 3px 0 0 #000000;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .composer-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .composer-tag {
    font-size: 0.72rem;
    font-weight: 700;
    color: #b45309;
  }

  .composer-header h3 {
    margin: 0;
    font-size: 1.25rem;
  }

  .macaly-scenario-textarea {
    width: 100%;
    background: #fafafa;
    border: 1px solid #000;
    border-radius: 10px;
    padding: 14px;
    font-family: "Inter", sans-serif;
    font-size: 0.95rem;
    line-height: 1.5;
    resize: vertical;
    box-sizing: border-box;
    outline: none;
  }

  .composer-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .composer-helpers {
    display: flex;
    gap: 8px;
  }

  .helper-pill {
    font-size: 0.72rem;
    background: #f0f0f0;
    border: 1px solid #ccc;
    padding: 4px 10px;
    border-radius: 12px;
  }

  .macaly-btn-black {
    background: #000;
    color: #fff;
    border: 1px solid #000;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.88rem;
    cursor: pointer;
    box-shadow: 2px 2px 0 #000;
  }

  .macaly-btn-black:hover:not(:disabled) {
    background: #2a2a2a;
  }

  .section-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #000;
    padding-bottom: 10px;
    margin-bottom: 18px;
  }

  .badge-tag {
    font-size: 0.72rem;
    font-weight: 700;
    background: #fff;
    border: 1px solid #000;
    padding: 3px 8px;
    border-radius: 6px;
    box-shadow: 1px 1px 0 #000;
  }

  .scenarios-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
  }

  .scenario-card {
    background: #fff;
    border: 1px solid #000;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 2px 2px 0 0 #000;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .sc-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .sc-top h4 {
    margin: 0;
    font-size: 0.95rem;
  }

  .status-pill.active {
    font-size: 0.65rem;
    font-weight: 700;
    background: #dcfce7;
    border: 1px solid #166534;
    color: #166534;
    padding: 2px 6px;
    border-radius: 6px;
  }

  .sc-prompt {
    font-size: 0.85rem;
    color: #444;
    line-height: 1.45;
    margin: 0;
    font-style: italic;
  }

  .sc-goals-tray {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .sc-goal-chip {
    font-size: 0.7rem;
    background: #ffd09b;
    border: 1px solid #000;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
  }

  .sc-footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.7rem;
    color: #666;
    border-top: 1px solid #eee;
    padding-top: 8px;
  }
</style>
