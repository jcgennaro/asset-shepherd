"""Long component inventories collapse without dropping review or form controls."""

import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from asset_shepherd.web import ComponentProposalView, InspectionCheckView
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
    assert html.count('form="decision"') == (count if editable else 0)
    for i in range(count):
        assert f'data-component-focus="body-{i}"' in html
    if count > 7:
        assert f"{count} sub-components" in html


@pytest.mark.skipif(find_chromium() is None, reason="Chromium is not installed")
def test_component_disclosure_preserves_hidden_form_values(tmp_path: Path) -> None:
    """Native disclosure opens/closes while every choice remains part of the same form."""
    page = tmp_path / "components.html"
    page.write_text(
        '<!doctype html><meta charset="utf-8"><form id="decision"></form>'
        + render_components(65)
        + """<script>
        function require(value, message) { if (!value) throw Error(message); }
        try {
          const pane = document.querySelector('details');
          const summary = pane.querySelector('summary');
          const form = document.getElementById('decision');
          require(!pane.open, 'must start collapsed');
          require([...new FormData(form)].length === 65, 'hidden choices omitted');
          summary.click(); require(pane.open, 'cannot expand');
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
            f"--user-data-dir={tmp_path / 'browser'}",
            "--dump-dom",
            page.as_uri(),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    assert b'data-component-test="PASS"' in result.stdout, result.stdout[-4000:]
