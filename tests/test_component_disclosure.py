"""Long component inventories collapse without dropping review or form controls."""

# pyright: reportPrivateUsage=false

import re
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from asset_shepherd.hosted_workspace import HostedWorkspaceError
from asset_shepherd.web import (
    ComponentProposalView,
    InspectionCheckView,
    _validate_component_choices,
)
from asset_shepherd.web_evidence_renderer import find_chromium

ROOT = Path(__file__).resolve().parents[1]


def render_components(count: int, *, editable: bool = True) -> str:
    """Render the shared live/history inspection partial with exact component IDs."""
    env = Environment(
        loader=FileSystemLoader(ROOT / "src/asset_shepherd/templates"),
        autoescape=select_autoescape(),
    )
    check = InspectionCheckView(
        label="Topology",
        status="warning",
        status_label="Review",
        description=f"{count} disconnected components",
        action="Review the proposed selection.",
        component_proposals=tuple(
            ComponentProposalView(f"body-{i}", f"C{i + 1}", "Measured component", i % 2 == 0)
            for i in range(count)
        ),
    )
    return env.get_template("_inspection_checklist.html").render(
        inspection_checks=[check], proposal_response_form_id="decision" if editable else ""
    )


@pytest.mark.parametrize("count", [0, 7, 8, 65])
@pytest.mark.parametrize("editable", [True, False])
def test_component_disclosure_threshold_and_complete_inventory(count: int, editable: bool) -> None:
    """Only lists longer than seven collapse, and no rows or form bindings are truncated."""
    html = render_components(count, editable=editable)
    assert ('<details class="component-disclosure">' in html) == (count > 7)
    assert '<details class="component-disclosure" open' not in html
    assert html.count('data-component-proposal="') == count
    assert html.count(' form="decision"') == (count if editable else 0)
    assert '<select name="response_component_' not in html
    assert "data-component-disposition" not in html
    assert html.count("data-component-toggle") == (count if editable else 0)
    for i in range(count):
        assert f'data-component-focus="body-{i}"' in html
    if count > 7:
        assert f"{count} sub-components" in html


def test_component_choices_require_a_survivor_before_dispatch() -> None:
    """All-remove and stale IDs fail; keeping either proposed or original survivor works."""
    components = (
        ComponentProposalView("a", "C1", "One", True),
        ComponentProposalView("b", "C2", "Two", False),
    )
    with pytest.raises(HostedWorkspaceError, match="Keep at least one"):
        _validate_component_choices(components, {"a": "accept", "b": "request_remove"})
    with pytest.raises(HostedWorkspaceError, match="no longer available"):
        _validate_component_choices(components, {"unknown": "accept"})
    _validate_component_choices(components, {"a": "reject", "b": "request_remove"})
    _validate_component_choices(components, {"a": "accept", "b": "accept"})
    _validate_component_choices(components, {})


@pytest.mark.skipif(find_chromium() is None, reason="Chromium is not installed")
@pytest.mark.parametrize("width", [420, 1200])
def test_component_disclosure_preserves_hidden_form_values(tmp_path: Path, width: int) -> None:
    """Real browser controls retain choices, block empty submission, and isolate hover boxes."""
    page = tmp_path / "components.html"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        + f'<link rel="stylesheet" href="{(ROOT / "src/asset_shepherd/static/app.css").as_uri()}">'
        + f"<style>body {{ width: {width}px; max-width: 100%; }}</style>"
        + '<div data-scene-notebook><main class="conversation-pane">'
        '<form id="decision" data-plan-response-form><button data-plan-response-submit>'
        "Apply recommendations <span>→</span></button></form>"
        + render_components(65)
        + '</main><aside id="comparison"><svg class="comparison-hud" data-comparison-hud>'
        '<g id="boxes">'
        '<g class="comparison-component-box component-color-4" '
        'data-component-id="body-0"></g><g class="comparison-component-box component-color-1" '
        'data-component-id="body-1"></g></g><g data-comparison-target="before"></g>'
        "</svg></aside></div>"
        + f'<script src="{(ROOT / "src/asset_shepherd/static/app.js").as_uri()}"></script>'
        + r"""<script>
        function require(value, message) { if (!value) throw Error(message); }
        try {
          const scene = {
            before: { minimum: [-3, -2, -1] }, after: { minimum: [7, 2, 3] },
            origins: { before: [0, 0, 0], after: [10, 0, 0] }
          };
          require(focusedAxisFrame(scene, 'both').target === 'before', 'initial axis focus');
          const afterFrame = focusedAxisFrame(scene, 'after');
          require(afterFrame.origin[0] === 10, 'after axes not at translated origin');
          require(focusedAxisFrame(scene, 'both', afterFrame.target).target === 'after',
            'both lost last focused model');
          require(focusedAxisFrame(scene, 'before', 'after').origin[0] === 0,
            'before axes not restored');
          require(focusedAxisFrame({before: scene.before}, 'both').origin[0] === 0,
            'single model origin');
          for (let axis = 0; axis < 3; axis++) {
            require(JSON.stringify(metricAxisPosition(afterFrame.origin, axis, 0)) ===
              '[10,0,0]', 'axis zero ticks diverge');
            const position = metricAxisPosition(afterFrame.origin, axis, 2);
            require(position[axis] === afterFrame.origin[axis] + 2, 'metric tick offset');
          }
          require(JSON.stringify(afterFrame.origin) === '[10,0,0]', 'origin mutated');
          const pane = document.querySelector('details');
          const summary = pane.querySelector('summary');
          const form = document.getElementById('decision');
          const submit = form.querySelector('button');
          const all = document.querySelector('[data-component-select-all]');
          const first = pane.querySelector('[data-component-toggle]');
          const firstValue = pane.querySelector('[data-component-response]');
          const comparison = document.getElementById('comparison');
          let boxes = document.getElementById('boxes');
          bindComponentHighlights(comparison, boxes);
          const ownBox = boxes.children[0], otherBox = boxes.children[1];
          require(ownBox.classList.contains('removed'), 'initial removal not synced');
          require(ownBox.classList.contains('component-color-0'), 'palette mismatches row');
          require(!otherBox.classList.contains('removed'), 'initial kept box gray');
          require(all.indeterminate && !all.checked, 'mixed initial state missing');
          require(first.getAttribute('aria-pressed') === 'false', 'initial Remove not reflected');
          require(firstValue.value === 'accept', 'initial approval changed');
          all.click();
          require(all.checked && !all.indeterminate, 'select all did not keep all');
          require(firstValue.value === 'reject', 'keep did not reject proposed removal');
          require(!ownBox.classList.contains('removed'), 'select all did not color box');
          all.click();
          require(!all.checked && submit.disabled, 'empty selection must disable continue');
          require(ownBox.classList.contains('removed') && otherBox.classList.contains('removed'),
            'deselect all did not gray boxes');
          require(!document.querySelector('[data-component-selection-error]').hidden,
            'empty hint hidden');
          const blocked = new Event('submit', {bubbles: true, cancelable: true});
          form.dispatchEvent(blocked);
          require(blocked.defaultPrevented, 'empty submit was not blocked');
          require(!pane.open, 'must start collapsed');
          require([...new FormData(form)].length === 65, 'hidden choices omitted');
          summary.click(); require(pane.open, 'cannot expand');
          first.click();
          require(!submit.disabled && all.indeterminate, 'one survivor did not re-enable continue');
          require(first.getBoundingClientRect().right <= document.body.clientWidth,
            'component row overflows narrow layout');
          require(first.classList.contains('keep') && first.getAttribute('aria-pressed') === 'true',
            'Keep style/state missing');
          require(!/\b(Keep|Remove)\b/.test(first.textContent), 'visible disposition words remain');
          const keptColor = getComputedStyle(first).getPropertyValue('--component-color');
          first.click();
          require(first.classList.contains('remove') &&
            first.getAttribute('aria-pressed') === 'false',
            'Remove style/state missing');
          require(getComputedStyle(first).getPropertyValue('--component-color') !== keptColor,
            'Remove not grayscale');
          first.click();
          first.dispatchEvent(new Event('pointerenter'));
          require(ownBox.classList.contains('active') && otherBox.classList.contains('muted'),
            'hover not isolated');
          require(getComputedStyle(otherBox).opacity === '0.28', 'other box not dimmed');
          const target = comparison.querySelector('[data-comparison-target]');
          require(getComputedStyle(target).opacity === '0.28', 'overall box not dimmed');
          first.dispatchEvent(new Event('pointerleave'));
          require(!otherBox.classList.contains('muted'), 'hover dimming stuck');
          require(otherBox.classList.contains('removed'), 'hover lost removal state');
          first.click();
          first.dispatchEvent(new Event('pointerenter'));
          require(ownBox.classList.contains('active'), 'removed box cannot be highlighted');
          first.dispatchEvent(new Event('pointerleave'));
          require(!ownBox.classList.contains('active') && ownBox.classList.contains('removed'),
            'removed box not restored after hover');
          first.click();
          first.focus();
          require(otherBox.classList.contains('muted'), 'keyboard focus not isolated');
          require(first.getAttribute('aria-pressed') === 'true', 'highlight changed selection');
          first.blur();
          require(!otherBox.classList.contains('muted'), 'blur dimming stuck');
          // A scene replacement or sidebar/inline move must retain bindings and selection.
          const replacement = boxes.cloneNode(true);
          boxes.replaceWith(replacement); boxes = replacement;
          document.querySelector('.conversation-pane').append(comparison);
          bindComponentHighlights(comparison, boxes);
          first.dispatchEvent(new Event('pointerenter'));
          require(boxes.children[1].classList.contains('muted'), 'replacement hover unbound');
          first.dispatchEvent(new Event('pointerleave'));
          all.click();
          require([...boxes.children].every(box => !box.classList.contains('removed')),
            'replacement selection did not sync');
          const last = pane.querySelector('[name="response_component_body-64"]');
          last.value = 'reject';
          summary.click(); require(!pane.open, 'cannot collapse');
          require(new FormData(form).get(last.name) === 'reject', 'collapsed choice lost');
          summary.click(); require(pane.open && last.value === 'reject', 'reopened choice lost');
          require(pane.querySelectorAll('[data-component-focus]').length === 65, 'rows missing');
          document.body.dataset.componentTest = 'PASS';
        } catch (error) { document.body.dataset.componentTest = 'FAIL: ' + error.message; }
        </script>""",
        encoding="utf-8",
    )
    browser = find_chromium()
    assert browser is not None
    result = subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-first-run",
            f"--window-size={width},900",
            f"--screenshot={tmp_path / 'component-selection.png'}",
            f"--user-data-dir={tmp_path / 'browser'}",
            "--dump-dom",
            page.as_uri(),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    marker = re.search(rb'data-component-test="([^"]+)"', result.stdout)
    assert marker is not None and marker.group(1) == b"PASS", (
        marker.group(1) if marker else result.stdout[:1500]
    )
