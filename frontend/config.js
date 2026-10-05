// Backend URL - configurable per environment.
// In Vercel Services, frontend and backend share a domain, so we
// use a relative path. Locally we point at the localhost backend.
window.BEAD_API_BASE = (function() {
    if (typeof window === "undefined") return "http://127.0.0.1:8000";
    const host = window.location.hostname;
    // If we're on localhost, talk to the local backend
    if (host === "localhost" || host === "127.0.0.1") {
        return "http://127.0.0.1:8000";
    }
    // In production (Vercel), the backend is on the same domain under /api
    return "";
})();
