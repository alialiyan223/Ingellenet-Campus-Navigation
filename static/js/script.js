/**
 * Ingellenet Web App - Frontend Logic
 * Handles: Campus Map Rendering (Canvas), AI Queries, Real-time Status Updates
 */

const API = "http://127.0.0.1:5000/api";

// ── State ──────────────────────────────────────────────────────────────────────
let mapData = { rooms: {}, edges: [] };
let currentPath = [];
let selectedSource = null;
let selectedTarget = null;
let hoveredNode = null;
let animFrame = null;
let particles = [];

const COLORS = {
    bg:       "#0f172a",
    card:     "rgba(30,41,59,0.8)",
    edge:     "#1e293b",
    node:     "#475569",
    lab:      "#38bdf8",
    library:  "#818cf8",
    cafeteria:"#f472b6",
    washroom: "#fb7185",
    entrance: "#34d399",
    office:   "#fbbf24",
    health:   "#f97316",
    sports:   "#a78bfa",
    parking:  "#94a3b8",
    pathLine: "#34d399",
    start:    "#34d399",
    end:      "#fb7185",
    text:     "#94a3b8",
    highlight:"rgba(56,189,248,0.15)"
};

const ROOM_TYPE_COLORS = {
    lab:        COLORS.lab,
    library:    COLORS.library,
    cafeteria:  COLORS.cafeteria,
    washroom:   COLORS.washroom,
    entrance:   COLORS.entrance,
    office:     COLORS.office,
    health:     COLORS.health,
    sports:     COLORS.sports,
    parking:    COLORS.parking,
    classroom:  COLORS.node
};

// ── Canvas Setup ───────────────────────────────────────────────────────────────
const canvas = document.getElementById("map-canvas");
const ctx = canvas.getContext("2d");

function resizeCanvas() {
    const parent = canvas.parentElement;
    canvas.width  = parent.clientWidth;
    canvas.height = parent.clientHeight;
    drawMap();
}

window.addEventListener("resize", resizeCanvas);

// ── Fetch Map Data ─────────────────────────────────────────────────────────────
async function loadMap() {
    try {
        const res  = await fetch(`${API}/map`);
        const data = await res.json();
        mapData    = data;
        resizeCanvas();
        startParticles();
    } catch (e) {
        console.error("Could not load map:", e);
    }
}

// ── Drawing ────────────────────────────────────────────────────────────────────
function drawMap() {
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Background grid
    drawGrid(W, H);

    // Edges
    for (const edge of mapData.edges) {
        const r1 = mapData.rooms[edge.from];
        const r2 = mapData.rooms[edge.to];
        if (!r1 || !r2) continue;

        const onPath = currentPath.length > 1 &&
            currentPath.some((c, i) => i < currentPath.length-1 &&
                ((c===edge.from && currentPath[i+1]===edge.to) ||
                 (c===edge.to   && currentPath[i+1]===edge.from)));

        ctx.beginPath();
        ctx.moveTo(r1.x, r1.y);
        ctx.lineTo(r2.x, r2.y);
        ctx.strokeStyle = onPath ? COLORS.pathLine : COLORS.edge;
        ctx.lineWidth   = onPath ? 4 : 1.5;
        ctx.globalAlpha = onPath ? 0.9 : 0.4;
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    // Nodes
    for (const [code, room] of Object.entries(mapData.rooms)) {
        const isStart = code === currentPath[0];
        const isEnd   = code === currentPath[currentPath.length - 1];
        const onPath  = currentPath.includes(code);
        const color   = ROOM_TYPE_COLORS[room.room_type] || COLORS.node;

        const r = isStart || isEnd ? 10 : onPath ? 8 : 6;

        // Glow for path nodes
        if (onPath) {
            const gradient = ctx.createRadialGradient(room.x, room.y, 0, room.x, room.y, r * 3);
            gradient.addColorStop(0, color + "55");
            gradient.addColorStop(1, "transparent");
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(room.x, room.y, r * 3, 0, Math.PI * 2);
            ctx.fill();
        }

        // Node circle
        ctx.beginPath();
        ctx.arc(room.x, room.y, r, 0, Math.PI * 2);
        ctx.fillStyle = isStart ? COLORS.start : isEnd ? COLORS.end : color;
        ctx.fill();
        ctx.strokeStyle = "#0f172a";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label for important nodes
        const LABELED = ["lab","library","cafeteria","entrance","health","sports"];
        if (LABELED.includes(room.room_type) || onPath) {
            ctx.fillStyle = COLORS.text;
            ctx.font      = `${onPath ? "bold " : ""}10px Inter`;
            ctx.textAlign = "center";
            ctx.fillText(room.name, room.x, room.y + r + 13);
        }
    }

    // Particles
    updateParticles();

    // Hover effect
    if (hoveredNode && mapData.rooms[hoveredNode]) {
        const r = mapData.rooms[hoveredNode];
        ctx.beginPath();
        ctx.arc(r.x, r.y, 15, 0, Math.PI * 2);
        ctx.strokeStyle = COLORS.lab;
        ctx.setLineDash([5, 5]);
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

function drawGrid(W, H) {
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    const step = 40;
    for (let x = 0; x < W; x += step) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let y = 0; y < H; y += step) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }
}

// ── Particle System ────────────────────────────────────────────────────────────
function startParticles() {
    if (particles.length === 0) {
        particles = Array.from({ length: 20 }, () => ({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 2,
            speed: Math.random() * 0.5 + 0.1,
            opacity: Math.random()
        }));
    }

    if (animFrame) cancelAnimationFrame(animFrame);
    
    function loop() {
        drawMap();
        animFrame = requestAnimationFrame(loop);
    }
    loop();
}

function updateParticles() {
    for (const p of particles) {
        p.y -= p.speed;
        p.opacity -= 0.003;
        if (p.y < 0 || p.opacity <= 0) {
            p.x = Math.random() * canvas.width;
            p.y = canvas.height;
            p.opacity = Math.random();
        }
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(56,189,248,${p.opacity * 0.3})`;
        ctx.fill();
    }
}

// ── AI Query ───────────────────────────────────────────────────────────────────
document.getElementById("ask-btn").addEventListener("click", handleQuery);
document.getElementById("ai-query").addEventListener("keydown", e => {
    if (e.key === "Enter") handleQuery();
});

async function handleQuery() {
    const query = document.getElementById("ai-query").value.trim();
    if (!query) return;

    document.getElementById("ai-message").textContent = "🤖 Thinking...";
    document.getElementById("directions-list").innerHTML =
        `<li style="color:var(--text-dim)">Processing your request...</li>`;

    try {
        const res  = await fetch(`${API}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        renderResponse(data);
    } catch (e) {
        document.getElementById("ai-message").textContent = "⚠️ Could not connect to AI backend.";
    }
}

function renderResponse(data) {
    const msgEl  = document.getElementById("ai-message");
    const listEl = document.getElementById("directions-list");
    msgEl.textContent  = data.message || "";
    listEl.innerHTML   = "";

    if (data.type === "navigation" && data.path_data) {
        currentPath = data.path_data.path || [];
        data.path_data.steps.forEach((step, i) => {
            const li = document.createElement("li");
            li.textContent = step;
            li.style.animationDelay = `${i * 80}ms`;
            listEl.appendChild(li);
        });
        const distLi = document.createElement("li");
        distLi.innerHTML = `<strong style="color:var(--primary)">Total: ~${(data.path_data.distance * 10).toFixed(0)}m</strong>`;
        listEl.appendChild(distLi);

    } else if (data.type === "search_results") {
        currentPath = [];
        (data.results || []).forEach(r => {
            const li = document.createElement("li");
            li.innerHTML = `<span style="color:var(--primary)">${r.name}</span> &mdash; ${r.building}, Floor ${r.floor}`;
            li.style.cursor = "pointer";
            li.addEventListener("click", () => highlightRoom(r.code));
            listEl.appendChild(li);
        });

    } else if (data.type === "location_info") {
        currentPath = [];
        const r  = data.room;
        const li = document.createElement("li");
        li.innerHTML = `
            <strong style="color:var(--primary)">${r.name}</strong><br>
            Building: ${r.building} &middot; Floor: ${r.floor}<br>
            Type: ${r.room_type} &middot; Capacity: ${r.capacity}
        `;
        listEl.appendChild(li);
        highlightRoom(r.code);

    } else {
        currentPath = [];
        const li = document.createElement("li");
        li.style.color = "var(--warning)";
        li.textContent = data.message || "No result found.";
        listEl.appendChild(li);
    }
}

function highlightRoom(code) {
    currentPath = [code];
}

// ── Canvas Interactivity ──────────────────────────────────────────────────────
canvas.addEventListener("mousemove", e => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    let closest = null, minDist = Infinity;
    for (const [code, r] of Object.entries(mapData.rooms)) {
        const d = Math.hypot(r.x - mx, r.y - my);
        if (d < minDist) { minDist = d; closest = code; }
    }
    hoveredNode = (closest && minDist < 30) ? closest : null;
    canvas.style.cursor = hoveredNode ? "pointer" : "default";
});

canvas.addEventListener("click", e => {
    if (hoveredNode) {
        const closest = hoveredNode;
        if (!selectedSource) {
            selectedSource = closest;
            document.getElementById("ai-message").textContent = `📍 Start: ${mapData.rooms[closest].name}. Now click a destination.`;
            currentPath = [closest]; // Immediate feedback
        } else {
            selectedTarget = closest;
            if (selectedSource === selectedTarget) {
                document.getElementById("ai-message").textContent = "You are already there! Pick a different destination.";
                return;
            }
            navigateBetween(selectedSource, selectedTarget);
            selectedSource = null;
            selectedTarget = null;
        }
    }
});

async function navigateBetween(src, tgt) {
    document.getElementById("ai-message").textContent = "🔍 Calculating route...";
    const res  = await fetch(`${API}/navigation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: src, target: tgt })
    });
    if (res.ok) {
        const data = await res.json();
        renderResponse({ type: "navigation", path_data: data, message: `Route found: ${data.distance} units` });
    } else {
        document.getElementById("ai-message").textContent = "⚠️ No path found between these rooms.";
    }
}

// ── Real-time Status ───────────────────────────────────────────────────────────
async function pollStatus() {
    try {
        const res  = await fetch(`${API}/status`);
        const data = await res.json();

        const loc = data.current_location;
        document.getElementById("loc-name").textContent =
            loc.name || "Unknown";
        document.getElementById("loc-code").textContent =
            `${loc.code} · Confidence: ${Math.round((data.confidence || 0) * 100)}%`;

        document.getElementById("sync-status").textContent = data.sync_status || "...";
        const synced = data.sync_status && data.sync_status.includes("Synced");
        document.getElementById("sync-status").style.color =
            synced ? "var(--success)" : "var(--text-dim)";
    } catch {
        document.getElementById("sync-status").textContent = "Server offline";
    }
}

// ── Boot ───────────────────────────────────────────────────────────────────────
loadMap();
pollStatus();
setInterval(pollStatus, 3000);
