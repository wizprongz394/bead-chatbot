/* ============================================================
   BEAD ELECTRONICS - Product Assistant frontend
   ============================================================ */

const API_BASE = "http://127.0.0.1:8000";

const state = {
    sessionId: null,
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
    suggestions: document.getElementById("suggestions"),
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
        els.statusText.textContent = "Offline";
    }
}

function addMessage(role, content, options = {}) {
    const wrapper = el("div", { class: "message " + role });
    const avatar = el("div", { class: "message-avatar" }, [role === "user" ? "You" : "B"]);
    const bubble = el("div", { class: "message-content" });

    const safe = escapeHtml(content).replace(/\n/g, "<br>");
    bubble.innerHTML = safe;

    if (options.products && options.products.length) {
        const grid = el("div", { class: "product-grid" });
        options.products.forEach((p) => {
            const card = el("div", { class: "product-card" });
            card.innerHTML =
                "<div class=\"product-part\">" + escapeHtml(p.item_number || "?") + "</div>" +
                "<div class=\"product-spec\"><span class=\"product-spec-label\">Type</span><span class=\"product-spec-value\">" + escapeHtml(p.pin_type || "-") + "</span></div>" +
                "<div class=\"product-spec\"><span class=\"product-spec-label\">Material</span><span class=\"product-spec-value\">" + escapeHtml(p.material || "-") + "</span></div>" +
                "<div class=\"product-spec\"><span class=\"product-spec-label\">Length</span><span class=\"product-spec-value\">" + escapeHtml(p.length_in || "-") + "</span></div>" +
                "<div class=\"product-spec\"><span class=\"product-spec-label\">Diameter</span><span class=\"product-spec-value\">" + escapeHtml(p.diameter_in || "-") + "</span></div>";
            grid.appendChild(card);
        });
        bubble.appendChild(grid);
    }

    if (options.evidence && options.evidence.length) {
        const seen = new Set();
        const sources = el("div", { class: "sources" });
        sources.appendChild(el("div", { class: "sources-title" }, ["Sources"]));
        options.evidence.forEach((e) => {
            const url = e.source_url;
            if (!url || seen.has(url)) return;
            seen.add(url);
            const title = e.source_title || url;
            const link = el("a", { class: "source-link", href: url, target: "_blank", rel: "noopener" }, [title]);
            sources.appendChild(link);
        });
        bubble.appendChild(sources);
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

function renderConstraints(state) {
    const ap = (state && state.active_problem) || {};
    const entries = [];
    Object.entries(FIELD_LABELS).forEach(([field, label]) => {
        const c = ap[field];
        if (!c || c.value === null || c.value === undefined) return;
        entries.push({ field: field, label: label, value: c.value, source: c.source || "user_stated" });
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
            item.appendChild(el("div", { class: "constraint-source" }, [e.source]));
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

        const r = await fetch(API_BASE + "/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        if (!r.ok) throw new Error("HTTP " + r.status);
        const data = await r.json();

        removeTyping();

        state.sessionId = data.session_id;
        addMessage("assistant", data.reply || "(no reply)", {
            products: data.products || [],
            evidence: data.evidence || [],
        });

        renderConstraints(data.state);
    } catch (e) {
        removeTyping();
        addMessage("assistant", "Sorry, I couldn't reach the assistant. Make sure the backend is running on port 8000.");
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
            "<div class=\"suggestions\" id=\"suggestions\">" +
            "<button class=\"suggestion\" data-msg=\"I need a square tandem pin for a medical device, material C51000\">Find a square tandem pin</button>" +
            "<button class=\"suggestion\" data-msg=\"What is the swaging process?\">What is swaging?</button>" +
            "<button class=\"suggestion\" data-msg=\"What materials does Bead work with?\">What materials does Bead offer?</button>" +
            "<button class=\"suggestion\" data-msg=\"I need 10,000 pieces of W018-584AC\">Request a quote</button>" +
            "</div>"
        })
    );
    attachSuggestionHandlers();
}

function attachSuggestionHandlers() {
    document.querySelectorAll(".suggestion").forEach((btn) => {
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
