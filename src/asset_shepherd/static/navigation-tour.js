/* Navigation help only: never clicks application controls or submits a workflow turn. */
(() => {
  const dialog = document.querySelector("[data-navigation-tour]");
  if (!dialog || typeof dialog.showModal !== "function") return;
  // Only an explicit opt-out persists, scoped to this browser, not the shared login.
  // Do not inherit the old automatic "seen" flag.
  const storageKey = "asset-shepherd:navigation-tour:opt-out:v2";
  const optOut = dialog.querySelector("[data-tour-opt-out]");
  const title = dialog.querySelector("[data-tour-title]");
  const copy = dialog.querySelector("[data-tour-copy]");
  const context = dialog.querySelector("[data-tour-context]");
  const count = dialog.querySelector("[data-tour-count]");
  const back = dialog.querySelector("[data-tour-back]");
  const next = dialog.querySelector("[data-tour-next]");
  const spotlight = dialog.querySelector("[data-tour-spotlight]");
  let index = 0;
  let returnFocus = null;

  function remembered() {
    for (const name of ["localStorage", "sessionStorage"]) {
      try { if (window[name].getItem(storageKey) === "skip") return true; } catch (_error) { /* Optional browser storage. */ }
    }
    return false;
  }

  function remember(skip) {
    for (const name of ["localStorage", "sessionStorage"]) {
      try {
        if (skip) window[name].setItem(storageKey, "skip");
        else window[name].removeItem(storageKey);
      } catch (_error) { /* Tour remains dismissible. */ }
    }
  }

  function steps() {
    const touch = window.matchMedia("(hover: none)").matches;
    return [
      {
        title: "Welcome!",
        copy: "Asset Shepherd helps you inspect, refine, and prepare 3D assets for games, with you in control of the changes.",
        target: null, context: "Built for the Agents for Humans hackathon.",
      },
      {
        title: "Your way back to Gallery",
        copy: "Click the mascot in the top-left corner to return to your assets. From Gallery, open an asset to pick up where you left off.",
        target: ".workspace-logo", context: "The logo is always your home button.",
      },
      {
        title: "Make room when you need it",
        copy: touch
          ? "The left arrow hides the navigation sidebar. Tap the arrow at the left edge to reveal it; the right arrow pins it open again."
          : "The left arrow hides the navigation sidebar. Move your pointer to the double line at the left edge to peek inside; the right arrow pins it open again.",
        target: document.querySelector(".app-shell.nav-collapsed") ? "[data-rail-reveal]" : "[data-rail-collapse]",
        context: "FAQ and the other help pages live in this sidebar.",
      },
      {
        title: "Scroll back without losing your place",
        copy: "Inside an asset, the conversation keeps earlier steps above the current one. Scroll to read them, or use the numbered sidebar links to jump there.",
        target: ".hosted-flow", context: "Reading an earlier step does not rewind or change the asset.",
      },
      {
        title: "Get a better look at the model",
        copy: touch
          ? "Inside an asset, the 3D view sits beside or below the conversation, depending on your screen width. Drag on the model to rotate it and pinch to zoom."
          : "Inside an asset, drag on the 3D view to rotate, right-drag to pan, and scroll over it to zoom. On a wide screen, drag the divider to give the model more room.",
        target: "[data-notebook-scene-host]", context: "On narrow screens, look below the conversation for the 3D view.",
      },
    ];
  }

  function positionSpotlight() {
    const selector = steps()[index].target;
    const target = selector ? document.querySelector(selector) : null;
    if (!dialog.open || !target) { spotlight.hidden = true; return; }
    const rect = target.getBoundingClientRect();
    const visible = rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < window.innerHeight && rect.right > 0;
    spotlight.hidden = !visible;
    if (!visible) return;
    const left = Math.max(3, rect.left - 5);
    const top = Math.max(3, rect.top - 5);
    spotlight.style.left = `${left}px`;
    spotlight.style.top = `${top}px`;
    spotlight.style.width = `${Math.max(0, Math.min(window.innerWidth - 3, rect.right + 5) - left)}px`;
    spotlight.style.height = `${Math.max(0, Math.min(window.innerHeight - 3, rect.bottom + 5) - top)}px`;
  }

  function render() {
    const step = steps()[index];
    title.textContent = step.title;
    copy.textContent = step.copy;
    context.textContent = step.context;
    count.textContent = `${index + 1} of ${steps().length}`;
    back.disabled = index === 0;
    next.textContent = index === steps().length - 1 ? "Got it" : "Next →";
    title.focus({ preventScroll: true });
    positionSpotlight();
  }

  function open() {
    if (dialog.open) return;
    returnFocus = document.activeElement;
    index = 0;
    optOut.checked = remembered();
    dialog.showModal();
    render();
  }

  dialog.querySelector("[data-tour-skip]").addEventListener("click", () => dialog.close());
  back.addEventListener("click", () => { if (index > 0) { index -= 1; render(); } });
  next.addEventListener("click", () => {
    if (index === steps().length - 1) dialog.close();
    else { index += 1; render(); }
  });
  dialog.addEventListener("close", () => {
    remember(optOut.checked);
    spotlight.hidden = true;
    if (returnFocus instanceof HTMLElement && returnFocus.isConnected) returnFocus.focus({ preventScroll: true });
  });
  window.addEventListener("resize", positionSpotlight);
  window.addEventListener("scroll", positionSpotlight, { passive: true });
  for (const button of document.querySelectorAll("[data-navigation-tour-open]")) {
    button.addEventListener("click", () => {
      remember(false);
      open();
    });
  }
  if (dialog.hasAttribute("data-tour-auto") && !remembered()) open();
})();
