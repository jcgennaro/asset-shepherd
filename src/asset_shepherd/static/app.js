window.scrollTo(0, 0);

for (const fileInput of document.querySelectorAll("[data-file-input]")) {
  const dropZone = fileInput.closest("[data-drop-zone]");
  const fileLabel = dropZone?.querySelector("[data-file-label]");
  const fileError = dropZone?.querySelector("[data-file-error]");
  if (!dropZone || !fileLabel) {
    continue;
  }

  function updateFileState() {
    const selected = fileInput.files?.[0];
    const valid = Boolean(selected && selected.name.toLowerCase().endsWith(".glb"));
    fileInput.setCustomValidity(valid || !selected ? "" : "Choose one GLB file.");
    fileLabel.textContent = selected ? selected.name : "Choose or drop your GLB";
    dropZone.classList.toggle("invalid", Boolean(selected && !valid));
    if (fileError) {
      fileError.textContent = selected && !valid ? "Choose one GLB file." : "";
    }
  }

  fileInput.addEventListener("change", updateFileState);
  for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "copy";
      }
      dropZone.classList.add("dragging");
    });
  }
  dropZone.addEventListener("dragleave", (event) => {
    if (!dropZone.contains(event.relatedTarget)) {
      dropZone.classList.remove("dragging");
    }
  });
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
    const dropped = event.dataTransfer?.files;
    if (!dropped || dropped.length !== 1 || !dropped[0].name.toLowerCase().endsWith(".glb")) {
      fileInput.value = "";
      fileInput.setCustomValidity("Choose one GLB file.");
      fileLabel.textContent = "Choose or drop your GLB";
      dropZone.classList.add("invalid");
      if (fileError) {
        fileError.textContent = "Choose one GLB file.";
      }
      return;
    }
    fileInput.files = dropped;
    updateFileState();
  });
}

const policyProposal = document.querySelector("[data-policy-proposal]");
const profileMode = document.querySelector("[data-profile-mode]");
const customToggle = document.querySelector("[data-custom-toggle]");
const customFields = document.querySelector("[data-custom-fields]");
const customStatus = document.querySelector("[data-custom-status]");
const customInputs = [...document.querySelectorAll("[data-custom-field]")];
const selectedPolicyLabel = document.querySelector("[data-selected-policy]");

function populateCustomFields() {
  const defaults = JSON.parse(policyProposal?.dataset.profileDefaults || "{}");
  for (const input of customInputs) {
    const key = input.dataset.customField;
    const value = defaults[key];
    input.value = typeof value === "boolean" ? String(value) : value;
  }
}

function updateSelectedPolicyLabel() {
  if (!selectedPolicyLabel) {
    return;
  }
  selectedPolicyLabel.textContent = customToggle?.checked
    ? "Agent-resolved rules — adjusted"
    : "Agent-resolved rules";
}

function setCustomMode(enabled) {
  if (profileMode) {
    profileMode.value = enabled ? "custom" : "resolved";
  }
  if (customFields) {
    customFields.hidden = !enabled;
  }
  for (const input of customInputs) {
    input.disabled = !enabled;
    input.required = enabled;
  }
  if (customStatus) {
    customStatus.textContent = enabled
      ? "Your supported adjustments will be validated and frozen."
      : "Agent proposal remains active.";
  }
  updateSelectedPolicyLabel();
}

customToggle?.addEventListener("change", () => {
  populateCustomFields();
  setCustomMode(customToggle.checked);
});

populateCustomFields();
setCustomMode(false);

const intakeWorkflow = document.querySelector("[data-intake-workflow]");

if (intakeWorkflow) {
  const panels = [...intakeWorkflow.querySelectorAll("[data-intake-panel]")];
  const stepButtons = [...intakeWorkflow.querySelectorAll("[data-intake-step-button]")];
  const validationMessage = intakeWorkflow.querySelector("[data-step-validation]");

  function validateRules() {
    for (const input of customInputs) {
      if (!input.disabled && !input.checkValidity()) {
        input.reportValidity();
        return false;
      }
    }
    if (validationMessage) {
      validationMessage.textContent = "";
    }
    updateSelectedPolicyLabel();
    return true;
  }

  function showStep(step) {
    if (step === "upload" && !validateRules()) {
      return;
    }
    for (const panel of panels) {
      panel.hidden = panel.dataset.intakePanel !== step;
    }
    for (const button of stepButtons) {
      if (button.dataset.intakeStepButton === step) {
        button.setAttribute("aria-current", "step");
      } else {
        button.removeAttribute("aria-current");
      }
    }
    intakeWorkflow.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  for (const button of intakeWorkflow.querySelectorAll("[data-intake-next]")) {
    button.addEventListener("click", () => showStep(button.dataset.intakeNext));
  }
  for (const button of stepButtons) {
    button.addEventListener("click", () => showStep(button.dataset.intakeStepButton));
  }
}

for (const textarea of document.querySelectorAll("textarea")) {
  textarea.addEventListener("keydown", (event) => {
    const isCtrlEnter =
      event.key === "Enter" &&
      event.ctrlKey &&
      !event.altKey &&
      !event.metaKey &&
      !event.shiftKey;
    if (!isCtrlEnter) {
      return;
    }
    const form = textarea.form;
    const submitButton = form?.querySelector('button[type="submit"]:not([disabled])');
    if (!(form instanceof HTMLFormElement) || !(submitButton instanceof HTMLButtonElement)) {
      return;
    }
    event.preventDefault();
    form.requestSubmit(submitButton);
  });
}

function showWorkflowActivity(form) {
  const activityUrl = form.dataset.activityUrl;
  if (!activityUrl) {
    return;
  }
  const host = form.closest(".conversation-pane") || form.parentElement;
  if (!host) {
    return;
  }
  let trace = host.querySelector("[data-workflow-activity]");
  if (!trace) {
    trace = document.createElement("ol");
    trace.className = "workflow-activity";
    trace.dataset.workflowActivity = "";
    trace.setAttribute("role", "status");
    trace.setAttribute("aria-live", "polite");
    host.append(trace);
  }

  const render = (payload) => {
    const items = Array.isArray(payload?.items) ? payload.items.slice(-3) : [];
    trace.replaceChildren();
    for (const item of items) {
      const row = document.createElement("li");
      const status = document.createElement("span");
      const label = document.createElement("span");
      const itemStatus = item?.status || "ACTIVE";
      row.className = `workflow-activity-item ${itemStatus.toLowerCase()}`;
      status.className = "workflow-activity-status";
      status.setAttribute("aria-hidden", "true");
      status.textContent = itemStatus === "COMPLETE" ? "✓" : itemStatus === "ERROR" ? "!" : "";
      label.textContent = typeof item?.label === "string" ? item.label : "Running a bounded check";
      row.append(status, label);
      trace.append(row);
    }
  };

  render({ items: [{ label: "Starting the agent", status: "ACTIVE" }] });

  const poll = async () => {
    try {
      const response = await fetch(activityUrl, { cache: "no-store" });
      if (response.ok) {
        const payload = await response.json();
        render(payload);
        if (payload.state === "RUNNING") {
          window.setTimeout(poll, 400);
        }
      }
    } catch (_error) {
      window.setTimeout(poll, 800);
    }
  };
  window.setTimeout(poll, 250);
}

for (const form of document.querySelectorAll("[data-busy-form]")) {
  form.addEventListener("submit", (event) => {
    const submitter = event.submitter;
    for (const button of form.querySelectorAll("[data-submit-button]")) {
      if (button !== submitter) {
        button.disabled = true;
      }
    }
    if (submitter) {
      submitter.dataset.originalLabel = submitter.textContent;
      submitter.textContent = form.dataset.activityUrl ? "Starting…" : "Submitting…";
      submitter.setAttribute("aria-busy", "true");
      submitter.style.pointerEvents = "none";
    }
    if (form.dataset.activityUrl) {
      const scope = form.closest(".conversation-pane");
      if (scope) {
        scope.classList.add("is-working");
        scope.setAttribute("aria-busy", "true");
      }
    }
    showWorkflowActivity(form);
  });
}

for (const form of document.querySelectorAll("[data-plan-response-form]")) {
  const submit = form.querySelector("[data-plan-response-submit]");
  const dispositions = Array.from(
    document.querySelectorAll(`[form="${form.id}"][data-proposal-disposition]`),
  );
  const sync = () => {
    let requestsRevision = false;
    for (const disposition of dispositions) {
      const response = disposition.closest("[data-proposal-response]");
      const comment = response?.querySelector("[data-proposal-comment]");
      const isComment = disposition.value === "comment";
      if (comment instanceof HTMLTextAreaElement) {
        comment.hidden = !isComment;
        comment.required = isComment;
      }
      requestsRevision ||= disposition.value !== "accept";
    }
    if (submit instanceof HTMLButtonElement) {
      submit.value = requestsRevision ? "revise" : "approve";
      const label = submit.firstChild;
      if (label) {
        label.textContent = requestsRevision ? "Revise plan " : "Approve ";
      }
    }
  };
  for (const disposition of dispositions) {
    disposition.addEventListener("change", sync);
  }
  sync();
}

for (const form of document.querySelectorAll("[data-result-accept]")) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const review = form.closest("[data-result-review]");
    const question = review?.querySelector("[data-result-question]");
    const accepted = review?.querySelector("[data-result-accepted]");
    const button = form.querySelector("button[type='submit']");
    if (!review || !accepted || !button) {
      form.submit();
      return;
    }
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Saving…";
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Asset-Shepherd-Transition": "accept" },
      });
      if (!response.ok) {
        throw new Error(`Acceptance failed with ${response.status}`);
      }
      if (question) {
        question.hidden = true;
      }
      accepted.hidden = false;
      const heading = accepted.querySelector("[data-result-title]");
      if (heading?.id) {
        review.setAttribute("aria-labelledby", heading.id);
      }
      heading?.focus();
    } catch (_error) {
      let message = review.querySelector("[data-result-error]");
      if (!message) {
        message = document.createElement("p");
        message.className = "form-error";
        message.dataset.resultError = "";
        message.setAttribute("role", "alert");
        review.append(message);
      }
      message.textContent = "Could not save that choice. Try again.";
      button.disabled = false;
      button.textContent = originalLabel;
    }
  });
}

const jobContractDialog = document.querySelector("[data-job-contract-dialog]");
const jobContractOpen = document.querySelector("[data-job-contract-open]");
const jobContractClose = document.querySelector("[data-job-contract-close]");

if (jobContractDialog instanceof HTMLDialogElement && jobContractOpen) {
  jobContractOpen.addEventListener("click", () => jobContractDialog.showModal());
  jobContractClose?.addEventListener("click", () => jobContractDialog.close());
  jobContractDialog.addEventListener("click", (event) => {
    if (event.target === jobContractDialog) {
      jobContractDialog.close();
    }
  });
}

const descriptionExamplesDialog = document.querySelector(
  "[data-description-examples-dialog]",
);
const descriptionExamplesOpen = document.querySelector(
  "[data-description-examples-open]",
);
const descriptionExamplesClose = document.querySelector(
  "[data-description-examples-close]",
);

if (descriptionExamplesDialog instanceof HTMLDialogElement && descriptionExamplesOpen) {
  descriptionExamplesOpen.addEventListener("click", () =>
    descriptionExamplesDialog.showModal(),
  );
  descriptionExamplesClose?.addEventListener("click", () =>
    descriptionExamplesDialog.close(),
  );
  descriptionExamplesDialog.addEventListener("click", (event) => {
    if (event.target === descriptionExamplesDialog) {
      descriptionExamplesDialog.close();
    }
  });
}

for (const viewer of document.querySelectorAll("model-viewer")) {
  viewer.addEventListener("error", () => {
    viewer.classList.add("viewer-error");
    viewer.setAttribute("aria-label", `${viewer.getAttribute("alt")} — preview unavailable`);
  });
}

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

function createSvgElement(name, className) {
  const element = document.createElementNS(SVG_NAMESPACE, name);
  if (className) {
    element.setAttribute("class", className);
  }
  return element;
}

function initializeModelComparison(comparison) {
  const viewer = comparison.querySelector("[data-comparison-viewer]");
  const hud = comparison.querySelector("[data-comparison-hud]");
  const configElement = comparison.querySelector("[data-comparison-config]");
  const status = comparison.querySelector("[data-comparison-status]");
  const axesButton = comparison.querySelector("[data-comparison-axes]");
  const bananaButton = comparison.querySelector("[data-comparison-banana]");
  const afterModel = comparison.querySelector("[data-after-model]");
  const bananaModel = comparison.querySelector("[data-banana-model]");
  const axisLayer = comparison.querySelector("[data-comparison-axis-layer]");
  const bananaLayer = comparison.querySelector("[data-comparison-banana-layer]");
  if (!viewer || !hud || !configElement || !axisLayer || !bananaLayer) {
    return;
  }

  const config = JSON.parse(configElement.textContent || "{}");
  const afterLabel = comparison.dataset.afterLabel || "After";
  const sourceOnly = comparison.classList.contains("source-only");
  const workingScope = comparison.closest(".conversation-pane");
  let activeFitMode = "both";
  let axesVisible = false;
  let bananaVisible = false;
  let renderFrame = 0;
  let orbitHudFrame = 0;
  let bananaFinalOffset = null;
  let bananaAnimationFrame = 0;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fitButtons = [...comparison.querySelectorAll("[data-comparison-fit]")];
  const targetGraphics = new Map();
  const originGraphics = new Map();
  const axisGraphics = new Map();
  const boundingBoxEdges = [
    [0, 1], [0, 2], [0, 4],
    [1, 3], [1, 5], [2, 3],
    [2, 6], [3, 7], [4, 5],
    [4, 6], [5, 7], [6, 7],
  ];

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function adaptiveMetricUnit(longestM) {
    if (longestM >= 1000) {
      return { symbol: "km", multiplier: 0.001 };
    }
    if (longestM >= 1) {
      return { symbol: "m", multiplier: 1 };
    }
    if (longestM >= 0.01) {
      return { symbol: "cm", multiplier: 100 };
    }
    return { symbol: "mm", multiplier: 1000 };
  }

  function formatBoundsDimensions(bounds) {
    const unit = adaptiveMetricUnit(bounds.longest);
    const dimensions = bounds.maximum.map(
      (maximum, index) => (maximum - bounds.minimum[index]) * unit.multiplier,
    );
    const values = dimensions.map((value) => Number(value.toPrecision(3)));
    return `X ${values[0]} × Y ${values[1]} × Z ${values[2]} ${unit.symbol}`;
  }

  function hotspotPoint(name) {
    if (typeof viewer.queryHotspot !== "function") {
      return null;
    }
    const hotspot = viewer.queryHotspot(name);
    const point = hotspot?.canvasPosition;
    if (!point || ![point.x, point.y, point.z].every(Number.isFinite)) {
      return null;
    }
    return point;
  }

  for (const target of ["before", "after"]) {
    const layer = comparison.querySelector(`[data-comparison-target="${target}"]`);
    if (!layer) {
      continue;
    }
    const box = createSvgElement("path", `comparison-target-box ${target}`);
    const leader = createSvgElement("path", `comparison-leader ${target}`);
    const label = createSvgElement("text", `comparison-target-label ${target}`);
    layer.append(box, leader, label);
    targetGraphics.set(target, { layer, box, leader, label });
  }

  for (const target of ["before", "after"]) {
    const layer = comparison.querySelector(`[data-comparison-origin="${target}"]`);
    if (!layer) {
      continue;
    }
    const marker = createSvgElement("path", `comparison-origin-marker ${target}`);
    const label = createSvgElement("text", `comparison-origin-label ${target}`);
    layer.append(marker, label);
    originGraphics.set(target, { layer, marker, label });
  }

  const axisAnchors = [...viewer.querySelectorAll("[data-axis-anchor]")];
  for (const axis of ["x", "y", "z"]) {
    const anchors = axisAnchors
      .filter((anchor) => anchor.dataset.axisAnchor === axis)
      .sort((left, right) => Number(left.dataset.axisIndex) - Number(right.dataset.axisIndex));
    const group = createSvgElement("g", `comparison-axis comparison-axis-${axis}`);
    const line = createSvgElement("line", "comparison-axis-line");
    group.append(line);
    const ticks = anchors.map((anchor) => {
      const mark = createSvgElement("line", "comparison-axis-mark");
      const label = createSvgElement("text", "comparison-axis-label");
      group.append(mark, label);
      return { anchor, mark, label };
    });
    axisLayer.append(group);
    axisGraphics.set(axis, { anchors, group, line, ticks });
  }

  const bananaBox = createSvgElement("path", "comparison-banana-box");
  const bananaLeader = createSvgElement("path", "comparison-banana-leader");
  const bananaLabel = createSvgElement("text", "comparison-banana-label");
  bananaLabel.textContent = "20 cm banana";
  bananaLayer.append(bananaBox, bananaLeader, bananaLabel);

  function drawTarget(target) {
    const graphics = targetGraphics.get(target);
    if (!graphics) {
      return;
    }
    const points = Array.from({ length: 8 }, (_, index) =>
      hotspotPoint(`hotspot-${target}-${index}`),
    );
    if (points.some((point) => !point)) {
      graphics.layer.setAttribute("visibility", "hidden");
      return;
    }
    graphics.layer.removeAttribute("visibility");
    const width = viewer.clientWidth;
    const height = viewer.clientHeight;
    const rawLeft = Math.min(...points.map((point) => point.x));
    const rawRight = Math.max(...points.map((point) => point.x));
    const rawTop = Math.min(...points.map((point) => point.y));
    const rawBottom = Math.max(...points.map((point) => point.y));
    graphics.box.setAttribute(
      "d",
      boundingBoxEdges
        .map(([start, end]) =>
          `M${points[start].x} ${points[start].y}L${points[end].x} ${points[end].y}`,
        )
        .join(""),
    );

    if (sourceOnly && target === "before") {
      graphics.label.textContent = formatBoundsDimensions(config.before);
      graphics.label.setAttribute("x", clamp((rawLeft + rawRight) / 2, 8, width - 8));
      graphics.label.setAttribute(
        "y",
        clamp(rawTop > 34 ? rawTop - 14 : rawBottom + 22, 14, height - 8),
      );
      graphics.label.setAttribute("text-anchor", "middle");
      graphics.leader.setAttribute("visibility", "hidden");
      return;
    }

    graphics.leader.removeAttribute("visibility");
    const other = target === "before" ? "after" : "before";
    const tiny = Boolean(config[other]) && config[target].longest / config[other].longest < 0.18;
    const targetLabel = target === "after"
      ? afterLabel
      : comparison.dataset.beforeLabel || "Before";
    graphics.label.textContent = tiny ? `${targetLabel.toUpperCase()} MODEL HERE` : targetLabel.toUpperCase();
    const labelAbove = rawTop > 34;
    const labelY = clamp(labelAbove ? rawTop - 14 : rawBottom + 22, 14, height - 8);
    const labelX = clamp(target === "before" ? rawLeft : rawRight, 8, width - 8);
    const closestPoint = points.reduce((closest, point) => {
      const distance = Math.hypot(point.x - labelX, point.y - labelY);
      return distance < closest.distance ? { point, distance } : closest;
    }, { point: points[0], distance: Number.POSITIVE_INFINITY }).point;
    graphics.label.setAttribute("x", labelX);
    graphics.label.setAttribute("y", labelY);
    graphics.label.setAttribute("text-anchor", target === "before" ? "start" : "end");
    graphics.leader.setAttribute(
      "d",
      `M${labelX} ${labelY + (labelAbove ? 4 : -10)}L${closestPoint.x} ${closestPoint.y}`,
    );
  }

  function drawOrigin(target) {
    const graphics = originGraphics.get(target);
    if (!graphics) {
      return;
    }
    const point = hotspotPoint(`hotspot-${target}-origin`);
    if (!point) {
      graphics.layer.setAttribute("visibility", "hidden");
      return;
    }
    graphics.layer.removeAttribute("visibility");
    const radius = 7;
    graphics.marker.setAttribute(
      "d",
      `M${point.x - radius} ${point.y}H${point.x + radius}` +
        `M${point.x} ${point.y - radius}V${point.y + radius}` +
        `M${point.x - 3} ${point.y - 3}L${point.x + 3} ${point.y + 3}` +
        `M${point.x + 3} ${point.y - 3}L${point.x - 3} ${point.y + 3}`,
    );
    graphics.label.textContent = sourceOnly
      ? "ORIGIN"
      : `${target === "before" ? "BEFORE" : "AFTER"} ORIGIN`;
    graphics.label.setAttribute("x", clamp(point.x + 12, 8, viewer.clientWidth - 104));
    graphics.label.setAttribute("y", clamp(point.y - 10, 16, viewer.clientHeight - 8));
  }

  function renderAxes() {
    if (!axesVisible) {
      return;
    }
    for (const graphics of axisGraphics.values()) {
      const points = graphics.anchors.map((anchor) => hotspotPoint(anchor.getAttribute("slot")));
      if (points.some((point) => !point)) {
        graphics.group.setAttribute("visibility", "hidden");
        continue;
      }
      graphics.group.removeAttribute("visibility");
      const start = points[0];
      const end = points.at(-1);
      const length = Math.hypot(end.x - start.x, end.y - start.y) || 1;
      const perpendicularX = -(end.y - start.y) / length;
      const perpendicularY = (end.x - start.x) / length;
      const tickSpacing = length / Math.max(graphics.ticks.length - 1, 1);
      graphics.line.setAttribute("x1", start.x);
      graphics.line.setAttribute("y1", start.y);
      graphics.line.setAttribute("x2", end.x);
      graphics.line.setAttribute("y2", end.y);
      graphics.ticks.forEach(({ anchor, mark, label }, index) => {
        const point = points[index];
        mark.setAttribute("x1", point.x - perpendicularX * 4);
        mark.setAttribute("y1", point.y - perpendicularY * 4);
        mark.setAttribute("x2", point.x + perpendicularX * 4);
        mark.setAttribute("y2", point.y + perpendicularY * 4);
        label.setAttribute("x", point.x + perpendicularX * 9);
        label.setAttribute("y", point.y + perpendicularY * 9);
        label.textContent = anchor.dataset.axisLabel;
        label.setAttribute(
          "visibility",
          index === graphics.ticks.length - 1 || tickSpacing >= 24 ? "visible" : "hidden",
        );
      });
    }
  }

  function renderBanana() {
    if (!bananaVisible) {
      return;
    }
    const point = hotspotPoint("hotspot-banana");
    if (!point) {
      bananaLayer.setAttribute("visibility", "hidden");
      return;
    }
    bananaLayer.removeAttribute("visibility");
    const boxSize = 18;
    bananaBox.setAttribute(
      "d",
      `M${point.x - boxSize} ${point.y - boxSize / 2}h8m20 0h8` +
        `M${point.x - boxSize / 2} ${point.y - boxSize}v8m0 20v8`,
    );
    const labelX = clamp(point.x + 28, 8, viewer.clientWidth - 86);
    const labelY = clamp(point.y - 30, 16, viewer.clientHeight - 8);
    bananaLabel.setAttribute("x", labelX);
    bananaLabel.setAttribute("y", labelY);
    bananaLeader.setAttribute("d", `M${point.x + 8} ${point.y - 6}L${labelX - 4} ${labelY + 3}`);
  }

  function renderHud() {
    renderFrame = 0;
    hud.setAttribute("viewBox", `0 0 ${viewer.clientWidth} ${viewer.clientHeight}`);
    drawTarget("before");
    drawTarget("after");
    drawOrigin("before");
    drawOrigin("after");
    renderAxes();
    renderBanana();
  }

  function scheduleHud() {
    if (!renderFrame) {
      renderFrame = window.requestAnimationFrame(renderHud);
    }
  }

  function stopOrbitHudAnimation() {
    if (orbitHudFrame) {
      window.cancelAnimationFrame(orbitHudFrame);
      orbitHudFrame = 0;
    }
  }

  function renderOrbitHud() {
    orbitHudFrame = 0;
    if (!viewer.hasAttribute("auto-rotate") || document.hidden || !viewer.isConnected) {
      return;
    }
    renderHud();
    orbitHudFrame = window.requestAnimationFrame(renderOrbitHud);
  }

  function syncOrbitHudAnimation() {
    if (viewer.hasAttribute("auto-rotate") && !document.hidden) {
      if (!orbitHudFrame) {
        orbitHudFrame = window.requestAnimationFrame(renderOrbitHud);
      }
      return;
    }
    stopOrbitHudAnimation();
    scheduleHud();
  }

  function niceMeterStep(span) {
    const rawStep = Math.max(span, 1e-9) / 4;
    const magnitude = 10 ** Math.floor(Math.log10(rawStep));
    const fraction = rawStep / magnitude;
    const multiplier = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
    return multiplier * magnitude;
  }

  function updateAxes(bounds) {
    const spans = bounds.maximum.map((maximum, index) => maximum - bounds.minimum[index]);
    for (const [axisIndex, axis] of ["x", "y", "z"].entries()) {
      const graphics = axisGraphics.get(axis);
      if (!graphics) {
        continue;
      }
      const span = spans[axisIndex] > 1e-9 ? spans[axisIndex] : bounds.longest * 0.1;
      const step = niceMeterStep(span);
      graphics.anchors.forEach((anchor, index) => {
        const position = [...bounds.minimum];
        const value = index * step;
        position[axisIndex] += value;
        anchor.dataset.axisLabel =
          index === graphics.anchors.length - 1
            ? `${axis.toUpperCase()} · ${Number(value.toPrecision(3))} m`
            : index === 0
              ? ""
              : `${Number(value.toPrecision(3))} m`;
        viewer.updateHotspot({
          name: anchor.getAttribute("slot"),
          position: position.map((component) => `${component}m`).join(" "),
        });
      });
    }
  }

  function placeBanana(bounds) {
    const gap = Math.max(bounds.longest * 0.08, 0.02);
    const offset = [
      bounds.center[0],
      bounds.minimum[1] + 0.015916550531983376,
      bounds.minimum[2] - gap - 0.015987513586878777,
    ];
    bananaFinalOffset = offset;
    bananaModel?.setAttribute("offset", offset.join(" "));
    viewer.updateHotspot({
      name: "hotspot-banana",
      position: `${offset[0]}m ${offset[1] + 0.025}m ${offset[2]}m`,
    });
  }

  function setBananaPose(offset, scale, yawDegrees) {
    bananaModel?.setAttribute("offset", offset.join(" "));
    bananaModel?.setAttribute("scale", scale.join(" "));
    bananaModel?.setAttribute("orientation", `0deg 0deg ${yawDegrees}deg`);
    viewer.updateHotspot({
      name: "hotspot-banana",
      position: `${offset[0]}m ${offset[1] + 0.025 * scale[1]}m ${offset[2]}m`,
    });
    scheduleHud();
  }

  function cancelBananaAnimation() {
    if (bananaAnimationFrame) {
      window.cancelAnimationFrame(bananaAnimationFrame);
      bananaAnimationFrame = 0;
    }
  }

  function animateBananaIn(bounds) {
    cancelBananaAnimation();
    if (!bananaFinalOffset) {
      return;
    }
    const finalOffset = [...bananaFinalOffset];
    if (reduceMotion) {
      setBananaPose(finalOffset, [1, 1, 1], 0);
      return;
    }
    const flight = Math.max(bounds.longest * 1.4, 0.55);
    const startOffset = [
      finalOffset[0] - flight,
      finalOffset[1] + flight * 0.45,
      finalOffset[2] + flight * 0.25,
    ];
    let startedAt = 0;
    const animate = (timestamp) => {
      if (!startedAt) {
        startedAt = timestamp;
      }
      const progress = clamp((timestamp - startedAt) / 900, 0, 1);
      const eased = 1 - (1 - progress) ** 3;
      const arc = Math.sin(Math.PI * progress) * flight * 0.32;
      const offset = finalOffset.map(
        (value, index) =>
          startOffset[index] + (value - startOffset[index]) * eased + (index === 1 ? arc : 0),
      );
      const scale = 0.35 + 0.65 * eased;
      setBananaPose(offset, [scale, scale, scale], 720 * (1 - eased));
      if (progress < 1 && bananaVisible) {
        bananaAnimationFrame = window.requestAnimationFrame(animate);
      } else {
        bananaAnimationFrame = 0;
        if (bananaVisible) {
          setBananaPose(finalOffset, [1, 1, 1], 0);
        }
      }
    };
    bananaAnimationFrame = window.requestAnimationFrame(animate);
  }

  function animateBananaOut() {
    cancelBananaAnimation();
    if (!bananaFinalOffset || reduceMotion) {
      bananaModel?.setAttribute("scale", "0 0 0");
      bananaModel?.setAttribute("orientation", "0deg 0deg 0deg");
      return;
    }
    const startOffset = [...bananaFinalOffset];
    let startedAt = 0;
    const animate = (timestamp) => {
      if (!startedAt) {
        startedAt = timestamp;
      }
      const progress = clamp((timestamp - startedAt) / 650, 0, 1);
      const eased = progress * progress * (3 - 2 * progress);
      const offset = [
        startOffset[0],
        startOffset[1] - 0.012 * eased,
        startOffset[2],
      ];
      setBananaPose(
        offset,
        [1 + eased * 0.65, Math.max(1 - eased * 0.98, 0.02), 1 + eased * 0.8],
        0,
      );
      if (progress < 1) {
        bananaAnimationFrame = window.requestAnimationFrame(animate);
      } else {
        bananaAnimationFrame = 0;
        bananaModel?.setAttribute("scale", "0 0 0");
        bananaModel?.setAttribute("orientation", "0deg 0deg 0deg");
      }
    };
    bananaAnimationFrame = window.requestAnimationFrame(animate);
  }

  function frameBounds(bounds) {
    const spans = bounds.maximum.map((maximum, index) => maximum - bounds.minimum[index]);
    const radius = Math.max(Math.hypot(...spans) / 2, 1e-5);
    const verticalField = ((viewer.getFieldOfView?.() || 45) * Math.PI) / 180;
    const aspect = Math.max(viewer.clientWidth / viewer.clientHeight, 0.1);
    const horizontalField = 2 * Math.atan(Math.tan(verticalField / 2) * aspect);
    const limitingField = Math.min(verticalField, horizontalField);
    const distance = Math.max((radius / Math.tan(limitingField / 2)) * 1.04, 1e-7);
    viewer.cameraTarget = bounds.center.map((component) => `${component}m`).join(" ");
    viewer.cameraOrbit = `35deg 70deg ${distance}m`;
    viewer.fieldOfView = "45deg";
    scheduleHud();
  }

  function fit(mode) {
    cancelBananaAnimation();
    activeFitMode = mode;
    const bounds = config[mode];
    updateAxes(bounds);
    placeBanana(bounds);
    // Fit is always driven by the selected asset bounds. A 20 cm banana must not make a 1 cm
    // candidate occupy only a few pixels; it is a reference, never a camera target.
    frameBounds(bounds);
    if (bananaVisible && bananaFinalOffset) {
      setBananaPose(bananaFinalOffset, [1, 1, 1], 0);
    }
    for (const button of fitButtons) {
      const selected = button.dataset.comparisonFit === mode;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-pressed", String(selected));
    }
  }

  for (const button of fitButtons) {
    button.addEventListener("click", () => fit(button.dataset.comparisonFit));
  }
  axesButton?.addEventListener("click", () => {
    axesVisible = !axesVisible;
    axesButton.setAttribute("aria-pressed", String(axesVisible));
    axesButton.classList.toggle("active", axesVisible);
    axisLayer.toggleAttribute("hidden", !axesVisible);
    scheduleHud();
  });
  bananaButton?.addEventListener("click", () => {
    bananaVisible = !bananaVisible;
    bananaButton.setAttribute("aria-pressed", String(bananaVisible));
    bananaButton.classList.toggle("active", bananaVisible);
    if (bananaVisible) {
      bananaLayer.removeAttribute("hidden");
      fit(activeFitMode);
      animateBananaIn(config[activeFitMode]);
    } else {
      bananaLayer.setAttribute("hidden", "");
      animateBananaOut();
      updateAxes(config[activeFitMode]);
      frameBounds(config[activeFitMode]);
    }
  });

  viewer.addEventListener("camera-change", scheduleHud);
  viewer.addEventListener("load", () => {
    status?.setAttribute("hidden", "");
    afterModel?.setAttribute("aria-hidden", "true");
    window.setTimeout(() => fit("both"), 120);
  });
  viewer.addEventListener("error", () => {
    if (status) {
      status.textContent = "Comparison preview unavailable";
    }
  });
  new ResizeObserver(scheduleHud).observe(viewer);

  if (sourceOnly && workingScope) {
    const syncWorkingOrbit = () => {
      const shouldOrbit = workingScope.classList.contains("is-working") && !reduceMotion;
      viewer.toggleAttribute("auto-rotate", shouldOrbit);
      syncOrbitHudAnimation();
    };
    new MutationObserver(syncWorkingOrbit).observe(workingScope, {
      attributes: true,
      attributeFilter: ["class"],
    });
    document.addEventListener("visibilitychange", syncOrbitHudAnimation);
    syncWorkingOrbit();
  }
}

if (document.querySelector("[data-model-comparison]")) {
  customElements.whenDefined("model-viewer").then(() => {
    document.querySelectorAll("[data-model-comparison]").forEach(initializeModelComparison);
  });
}

const inspectionExperience = document.querySelector("[data-inspection-experience]");

if (inspectionExperience && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const rows = [...inspectionExperience.querySelectorAll("[data-inspection-check]")];
  const results = [...inspectionExperience.querySelectorAll("[data-inspection-result]")];
  const count = inspectionExperience.querySelector("[data-inspection-count]");
  inspectionExperience.classList.add("replaying");
  if (count) {
    count.textContent = `0 of ${rows.length}`;
  }
  for (const row of rows) {
    row.classList.remove(row.dataset.status);
    row.classList.add("replaying");
    row.querySelector(".inspection-check-icon").textContent = "…";
    row.querySelector("strong").textContent = `Checking ${row.dataset.label}…`;
  }
  results.forEach((result) => result.setAttribute("aria-hidden", "true"));

  rows.forEach((row, index) => {
    window.setTimeout(() => {
      const status = row.dataset.status;
      row.classList.remove("replaying");
      row.classList.add(status);
      row.querySelector("strong").textContent = row.dataset.label;
      row.querySelector(".inspection-check-icon").textContent =
        status === "pass"
          ? "✓"
          : status === "repaired"
            ? "!→✓"
            : status === "blocked"
              ? "×"
              : status === "checking"
                ? "…"
                : "!";
      if (count) {
        count.textContent = `${index + 1} of ${rows.length}`;
      }
      if (index === rows.length - 1) {
        inspectionExperience.classList.remove("replaying");
        inspectionExperience.classList.add("replay-complete");
        results.forEach((result) => result.removeAttribute("aria-hidden"));
      }
    }, 220 * (index + 1));
  });
}
