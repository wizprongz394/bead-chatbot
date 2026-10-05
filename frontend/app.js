/* ============================================================
   BEAD ELECTRONICS - Product Assistant frontend (v3)
   Stateless backend: client holds conversation state
   ============================================================ */

const API_BASE = (function() {
    // Local dev: browser is on localhost, backend runs on port 8000
    const h = window.location.hostname;
    if (h === "localhost" || h === "127.0.0.1") {
        return "http://127.0.0.1:8000";
    }
    // Production: frontend and backend share the same Vercel domain.
    // API calls go to /api/*, routed to the backend service.
    return "";
})();

const state = {
    sessionId: null,
    currentState: null,      // full backend state from last response
    isSending: false,
};

const els = {
    messages: document.getElementById("messages"),
    input: document.getElementById("input"),
    sendBtn: document.getElementById("send-btn"),
    constraints: document.getElementById("constraints"),
    actions: document.getElementById("actions"),
    resetBtn: document.getElementById("reset-btn"),
    statusDot: document.getElementById("status-dot"),
    statusText: document.getElementById("status-text"),
};

function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([k, v]) => {
        if (k === "class") node.className = v;
        else if (k === "html") node.innerHTML = v;
        else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
        else node.setAttribute(k, v);
    });
    children.forEach((c) => {
        if (typeof c === "string") node.appendChild(document.createTextNode(c));
        else if (c) node.appendChild(c);
    });
    return node;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

async function checkHealth() {
    try {
        const r = await fetch(API_BASE + "/api/health");
        if (r.ok) {
            els.statusDot.classList.remove("offline");
            els.statusDot.classList.add("online");
            els.statusText.textContent = "Connected";
        } else { throw new Error(); }
    } catch (e) {
        els.statusDot.classList.remove("online");
        els.statusDot.classList.add("offline");
        els.statusText.textContent = "Backend offline - start uvicorn";
    }
}

function renderProductGrid(products) {
    const grid = el("div", { class: "product-grid" });
    products.forEach((p) => {
        const url = p.source_url || "";
        const card = url
            ? el("a", { class: "product-card", href: url, target: "_blank", rel: "noopener" })
            : el("div", { class: "product-card" });

        card.innerHTML =
            "<div class=\"product-part\">" + escapeHtml(p.item_number || "?") + "</div>" +
            "<div class=\"product-spec\"><span class=\"product-spec-label\">Type</span><span class=\"product-spec-value\">" + escapeHtml(p.pin_type || "-") + "</span></div>" +
            "<div class=\"product-spec\"><span class=\"product-spec-label\">Material</span><span class=\"product-spec-value\">" + escapeHtml(p.material || "-") + "</span></div>" +
            "<div class=\"product-spec\"><span class=\"product-spec-label\">Length</span><span class=\"product-spec-value\">" + escapeHtml(p.length_in || "-") + "</span></div>" +
            "<div class=\"product-spec\"><span class=\"product-spec-label\">Diameter</span><span class=\"product-spec-value\">" + escapeHtml(p.diameter_in || "-") + "</span></div>" +
            (url ? "<div class=\"product-link-hint\">View in catalog &rarr;</div>" : "");
        grid.appendChild(card);
    });
    return grid;
}

function renderComparisonTable(action) {
    const a = action.a || {};
    const b = action.b || {};
    const wrap = el("div", { class: "comparison-wrap" });
    const table = el("table", { class: "comparison-table" });

    const thead = el("thead");
    const headerRow = el("tr");
    headerRow.appendChild(el("th", {}, ["Field"]));
    headerRow.appendChild(el("th", { class: "col-a" }, [a.item_number || "A"]));
    headerRow.appendChild(el("th", { class: "col-b" }, [b.item_number || "B"]));
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = el("tbody");
    (action.rows || []).forEach((r) => {
        if (r.field === "item_number") return;
        const tr = el("tr", { class: r.same ? "same" : "diff" });
        tr.appendChild(el("td", { class: "field-label" }, [r.label]));
        tr.appendChild(el("td", { class: "value-a" }, [String(r.a)]));
        tr.appendChild(el("td", { class: "value-b" }, [String(r.b)]));
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);

    const legend = el("div", { class: "comparison-legend" });
    legend.innerHTML =
        "<span class=\"legend-item\"><span class=\"legend-dot same\"></span>Match</span>" +
        "<span class=\"legend-item\"><span class=\"legend-dot diff\"></span>Difference</span>";
    wrap.appendChild(legend);

    return wrap;
}

function renderSources(evidence) {
    const seen = new Set();
    const sources = el("div", { class: "sources" });
    sources.appendChild(el("div", { class: "sources-title" }, ["Sources"]));
    evidence.forEach((e) => {
        const url = e.source_url;
        if (!url || seen.has(url)) return;
        seen.add(url);
        sources.appendChild(el("a", {
            class: "source-link", href: url, target: "_blank", rel: "noopener",
        }, [e.source_title || url]));
    });
    return sources;
}

function renderSuggestions(suggestions, onPick) {
    const wrap = el("div", { class: "msg-suggestions" });
    suggestions.forEach((s) => {
        wrap.appendChild(el("button", {
            class: "msg-suggestion",
            onclick: () => onPick(s),
        }, [s]));
    });
    return wrap;
}

function renderRfiBlock(stateObj) {
    const ap = stateObj && stateObj.active_problem;
    if (!ap) return el("div");

    const lines = [];
    const fields = [
        ["item_number", "Item Number"],
        ["product_family", "Product Family"],
        ["pin_type", "Pin Type"],
        ["material", "Material"],
        ["end_type", "End Type"],
        ["application", "Application"],
        ["volume", "Volume"],
    ];
    fields.forEach(([k, label]) => {
        const c = ap[k];
        if (c && c.value !== null && c.value !== undefined) {
            lines.push(label + ": " + c.value);
        }
    });

    const newline = String.fromCharCode(10);
    const bodyText = "RFI from Bead Product Assistant" + newline + newline
        + lines.join(newline)
        + newline + newline
        + "(Generated by the Bead Product Assistant)";

    const wrap = el("div", { class: "rfi-block" });
    wrap.appendChild(el("div", { class: "rfi-title" }, ["RFI Summary"]));
    const pre = el("pre", { class: "rfi-pre" }, [lines.join(newline)]);
    wrap.appendChild(pre);

    const actions = el("div", { class: "rfi-actions" });

    const mailto = "mailto:info@beadelectronics.com"
        + "?subject=" + encodeURIComponent("RFI from Bead Product Assistant")
        + "&body=" + encodeURIComponent(bodyText);

    const emailBtn = el("a", {
        class: "rfi-primary",
        href: mailto,
        title: "Open your email client with this RFI pre-filled"
    }, ["Email this to Bead"]);
    actions.appendChild(emailBtn);

    const copyBtn = el("button", {
        class: "rfi-secondary",
        onclick: () => {
            navigator.clipboard.writeText(bodyText);
            copyBtn.textContent = "Copied";
            setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
        }
    }, ["Copy"]);
    actions.appendChild(copyBtn);

    wrap.appendChild(actions);
    return wrap;
}

function addMessage(role, content, options = {}) {
    const wrapper = el("div", { class: "message " + role });
    const avatar = el("div", { class: "message-avatar" }, [role === "user" ? "You" : "B"]);
    const bubble = el("div", { class: "message-content" });

    if (content) {
        const safe = escapeHtml(content).replace(/\n/g, "<br>");
        bubble.innerHTML = safe;
    }

    if (options.actions && options.actions.length) {
        options.actions.forEach((action) => {
            if (action.type === "comparison") {
                bubble.appendChild(renderComparisonTable(action));
            }
            if (action.type === "rfi_prefill" && options.state) {
                bubble.appendChild(renderRfiBlock(options.state));
            }
        });
    }

    if (options.products && options.products.length) {
        bubble.appendChild(renderProductGrid(options.products));
    }

    if (options.evidence && options.evidence.length) {
        bubble.appendChild(renderSources(options.evidence));
    }

    if (options.suggestions && options.suggestions.length) {
        bubble.appendChild(renderSuggestions(options.suggestions, sendMessage));
    }

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    els.messages.appendChild(wrapper);
    els.messages.scrollTop = els.messages.scrollHeight;
    return wrapper;
}

function addTyping() {
    const wrapper = el("div", { class: "message assistant", id: "typing-indicator" });
    wrapper.appendChild(el("div", { class: "message-avatar" }, ["B"]));
    const t = el("div", { class: "typing" });
    t.appendChild(el("div", { class: "typing-dot" }));
    t.appendChild(el("div", { class: "typing-dot" }));
    t.appendChild(el("div", { class: "typing-dot" }));
    wrapper.appendChild(t);
    els.messages.appendChild(wrapper);
    els.messages.scrollTop = els.messages.scrollHeight;
}

function removeTyping() {
    const t = document.getElementById("typing-indicator");
    if (t) t.remove();
}

const FIELD_LABELS = {
    product_family: "Product Family",
    application: "Application",
    mounting: "Mounting",
    pin_type: "Pin Type",
    material: "Material",
    end_type: "End Type",
    length_in_min: "Length (min)",
    length_in_max: "Length (max)",
    square_in_min: "Square (min)",
    square_in_max: "Square (max)",
    diameter_in_min: "Diameter (min)",
    diameter_in_max: "Diameter (max)",
    item_number: "Item Number",
    volume: "Volume",
};

function renderConstraints(stateObj) {
    const ap = (stateObj && stateObj.active_problem) || {};
    const entries = [];
    Object.entries(FIELD_LABELS).forEach(([field, label]) => {
        const c = ap[field];
        if (!c || c.value === null || c.value === undefined) return;
        entries.push({ field, label, value: c.value, source: c.source || "user_stated" });
    });

    els.constraints.innerHTML = "";
    if (!entries.length) {
        els.constraints.appendChild(
            el("div", { class: "empty-hint" }, ["No requirements captured yet. Start typing to begin."])
        );
        return;
    }
    entries.forEach((e) => {
        const inferred = e.source !== "user_stated";
        const item = el("div", { class: "constraint-item " + (inferred ? "inferred" : "") });
        item.appendChild(el("div", { class: "constraint-label" }, [e.label]));
        item.appendChild(el("div", { class: "constraint-value" }, [String(e.value)]));
        if (inferred) {
            item.appendChild(el("div", { class: "constraint-source" }, ["inferred"]));
        }
        els.constraints.appendChild(item);
    });
}

async function sendMessage(text) {
    if (state.isSending || !text.trim()) return;

    const welcome = els.messages.querySelector(".welcome");
    if (welcome) welcome.remove();

    addMessage("user", text);
    els.input.value = "";
    els.input.style.height = "auto";
    state.isSending = true;
    els.sendBtn.disabled = true;

    addTyping();

    try {
        const body = { message: text };
        if (state.sessionId) body.session_id = state.sessionId;
        if (state.currentState) body.state = state.currentState;

        const r = await fetch(API_BASE + "/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!r.ok) throw new Error("HTTP " + r.status);
        const data = await r.json();

        removeTyping();
        state.sessionId = data.session_id;
        state.currentState = data.state;  // store for next turn

        addMessage("assistant", data.reply || "(no reply)", {
            products: data.products || [],
            evidence: data.evidence || [],
            actions: data.actions || [],
            suggestions: data.suggestions || [],
            state: data.state,
        });

        renderConstraints(data.state);
    } catch (e) {
        removeTyping();
        addMessage("assistant",
            "Sorry, I couldn't reach the assistant. Make sure the backend is running.");
        console.error(e);
    } finally {
        state.isSending = false;
        els.sendBtn.disabled = false;
        els.input.focus();
    }
}

async function resetConversation() {
    if (state.sessionId) {
        try {
            await fetch(API_BASE + "/api/reset/" + state.sessionId, { method: "POST" });
        } catch (e) { /* ignore */ }
    }
    state.sessionId = null;
    state.currentState = null;
    els.messages.innerHTML = "";
    els.constraints.innerHTML = "";
    renderWelcome();
}

function renderWelcome() {
    els.messages.appendChild(
        el("div", { class: "welcome", html:
            "<div class=\"welcome-icon\">&#9889;</div>" +
            "<h1>Hi, I'm your Bead Product Assistant.</h1>" +
            "<p>Describe what you need in plain language, and I'll help you find the right contact pin or answer technical questions.</p>" +
            "<div class=\"suggestions\">" +
            "<button class=\"suggestion\" data-msg=\"I need a square tandem pin for a medical device, material C51000\">Find a square tandem pin</button>" +
            "<button class=\"suggestion\" data-msg=\"What is the swaging process?\">What is swaging?</button>" +
            "<button class=\"suggestion\" data-msg=\"Compare W018-584AC and W020-431AC\">Compare two products</button>" +
            "<button class=\"suggestion\" data-msg=\"Show me alternatives to W018-584AC\">Show alternatives</button>" +
            "</div>"
        })
    );
    attachSuggestionHandlers();
}

function attachSuggestionHandlers() {
    document.querySelectorAll(".suggestion").forEach((btn) => {
        if (btn._bound) return;
        btn._bound = true;
        btn.addEventListener("click", () => {
            sendMessage(btn.dataset.msg || btn.textContent.trim());
        });
    });
}

function autoResize() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 120) + "px";
}

els.input.addEventListener("input", autoResize);
els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(els.input.value);
    }
});
els.sendBtn.addEventListener("click", () => sendMessage(els.input.value));
els.resetBtn.addEventListener("click", resetConversation);

attachSuggestionHandlers();
checkHealth();
setInterval(checkHealth, 30000);
els.input.focus();

