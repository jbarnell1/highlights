// Keeps progress fresh while something is running, and asks before destructive buttons.
(() => {
  const base = document.body.dataset.base || "";
  const poll = document.body.dataset.poll;

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register(`${base}/sw.js`, { scope: `${base}/` }).catch(() => {});
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (form.dataset.ok) return;
      e.preventDefault();
      const btn = form.querySelector("button");
      const label = btn.textContent;
      btn.textContent = "Tap again to confirm";
      form.dataset.ok = "1";
      setTimeout(() => { delete form.dataset.ok; btn.textContent = label; }, 4000);
    });
  });

  // Stop double taps from queueing the same job twice.
  document.querySelectorAll("form[method=post]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (e.defaultPrevented) return;
      const btn = form.querySelector("button");
      if (btn) setTimeout(() => { btn.disabled = true; }, 0);
    });
  });

  const every = (ms, fn) => {
    let timer;
    const tick = async () => {
      if (document.visibilityState === "visible") {
        try { await fn(); } catch (_) { /* offline for a moment; try again next tick */ }
      }
      timer = setTimeout(tick, ms);
    };
    timer = setTimeout(tick, ms);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") { clearTimeout(timer); tick(); }
    });
  };

  if (poll === "event") {
    const id = document.body.dataset.event;
    const stage = document.body.dataset.stage;
    const line = document.getElementById("status-line");
    const meter = document.getElementById("meter");
    every(2000, async () => {
      const r = await fetch(`${base}/api/events/${id}`, { cache: "no-store" });
      const s = await r.json();
      if (s.stage !== stage || s.error) { location.reload(); return; }
      if (s.message && line) line.textContent = s.message;
      else if (s.queued && line) line.textContent = "Waiting for the job ahead of it";
      if (meter && s.progress != null) meter.style.width = `${Math.round(s.progress * 100)}%`;
    });
  }

  if (poll === "home") {
    let last = null;
    every(4000, async () => {
      const r = await fetch(`${base}/api/status`, { cache: "no-store" });
      const s = await r.json();
      const sig = JSON.stringify([s.stages, s.jobs.map((j) => [j.id, j.status])]);
      if (last !== null && sig !== last) { location.reload(); return; }
      last = sig;
      s.jobs.forEach((j) => {
        const bar = document.querySelector(`[data-job="${j.event_id}"] > span`);
        if (bar) bar.style.width = `${Math.round((j.progress || 0) * 100)}%`;
      });
    });
  }
})();
