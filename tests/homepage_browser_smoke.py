"""Exercise the public static homepage at both root and GitHub project paths."""
import functools
import importlib.util
import json
import os
import atexit
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("CTBENCH_ARTIFACTS") or tempfile.mkdtemp(prefix="ctbench-homepage-"))
ARTIFACTS.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build_site.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


preview_directory = tempfile.TemporaryDirectory()
builder.build(Path(preview_directory.name))
preview_server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=preview_directory.name))
preview_thread = threading.Thread(target=preview_server.serve_forever, daemon=True)
preview_thread.start()
preview_url = f"http://127.0.0.1:{preview_server.server_port}/"
def cleanup_preview():
    preview_server.shutdown()
    preview_server.server_close()
    preview_thread.join()
    preview_directory.cleanup()
atexit.register(cleanup_preview)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get("CTBENCH_BROWSER_CHANNEL"), headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1040}, permissions=["clipboard-read", "clipboard-write"], reduced_motion="reduce")
    page = context.new_page()
    errors, bad_responses = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("response", lambda response: bad_responses.append((response.status, response.url)) if response.status >= 400 else None)
    page.goto(preview_url, wait_until="networkidle")
    expect(page.locator("#leaderboard-body tr")).to_have_count(5)
    expect(page.locator("#source-label")).to_contain_text("Table 5")
    page.screenshot(path=str(ARTIFACTS / "desktop.png"), full_page=True)
    page.screenshot(path=str(ARTIFACTS / "hero.png"))
    assert page.locator(".network-panel").evaluate("el => getComputedStyle(el).transform") == "none"
    assert page.evaluate("""() => {
        const panel = document.querySelector('.network-panel').getBoundingClientRect();
        const hero = document.querySelector('.hero');
        return Math.abs(panel.right - hero.getBoundingClientRect().right + parseFloat(getComputedStyle(hero).paddingRight)) < 1;
    }""")
    paper = json.loads(builder.PUBLISHED.read_text(encoding="utf-8"))
    details = json.loads(builder.AGENT_DETAILS.read_text(encoding="utf-8"))
    dialog = page.get_by_role("dialog")
    for index, agent in enumerate(paper["results"]):
        opener = page.get_by_role("button", name=f"View details for {agent['harness']} + {agent['model']}", exact=True)
        opener.focus()
        opener.press("Enter")
        expect(dialog).to_be_visible()
        expect(dialog.locator("#agent-detail-title")).to_have_text(agent["model"])
        entry = next(row for row in details["agents"] if row["harness"] == agent["harness"] and row["model"] == agent["model"])
        for track in ("rca", "path"):
            dialog.locator(f"[data-detail-track={track}]").click()
            expect(dialog.locator(f"[data-detail-track={track}]")).to_have_attribute("aria-pressed", "true")
            expect(dialog.locator("#detail-score-context")).to_contain_text(f"{paper['tasks'][track]} tasks")
            for position, key in enumerate(("accuracy", "localization", "reasoning", "evidence")):
                expect(dialog.locator(".detail-score-card strong").nth(position)).to_have_text(f"{agent[track][key]['mean']:.2f}%")
            for position, key in enumerate(("rounds", "latency", "tokens")):
                metric = entry["efficiency"][track][key]
                card = dialog.locator(".efficiency-card").nth(position)
                expect(card).to_contain_text(metric["label"])
                if metric["status"] == "available":
                    expect(card).to_contain_text("Paper-reported value")
                    expect(card.locator("strong")).to_have_text(metric["displayValue"])
                    assert card.locator("strong").inner_text() != chr(8212)
                else:
                    expect(card.locator("strong")).to_have_text(chr(8212))
                    expect(card).to_contain_text("Not reported")
            expect(dialog.locator("#detail-efficiency-label a")).to_have_attribute("href", details["efficiencySource"]["url"])
            example = details.get("examples", {}).get(track)
            if example:
                expect(dialog.locator("#detail-example-kind")).to_have_text("Expert reference trace")
                expect(dialog.locator(".example-source-links a").first).to_have_attribute("href", example["sources"][0]["url"])
                expect(dialog.locator(".example-provenance")).to_contain_text(f"not a recorded run by {agent['harness']} + {agent['model']}")
                expect(dialog.locator(".example-question")).to_contain_text(example["id"])
                expect(dialog.locator(".trace-step")).to_have_count(len(example["steps"]))
            else:
                expect(dialog.locator("#detail-example-kind")).to_have_text("Example pending")
                expect(dialog.locator(".trace-step")).to_have_count(0)
        if details.get("examples", {}).get("path"):
            dialog.get_by_role("button", name="Expand all", exact=True).click()
            expect(dialog.locator(".trace-step[open]")).to_have_count(len(details["examples"]["path"]["steps"]))
            dialog.get_by_role("button", name="Collapse all", exact=True).click()
            expect(dialog.locator(".trace-step[open]")).to_have_count(0)
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        expect(opener).to_be_focused()
    page.get_by_role("button", name="View details for Codex + GPT-5.5", exact=True).click()
    dialog.locator(".agent-dialog-body").evaluate("el => el.scrollTop = 0")
    page.screenshot(path=str(ARTIFACTS / "agent-details-desktop.png"))
    dialog.locator("[data-detail-track=path]").click()
    dialog.locator(".example-section").scroll_into_view_if_needed()
    page.screenshot(path=str(ARTIFACTS / "agent-trace-desktop.png"))
    dialog.get_by_label("Select agent for details").select_option("1")
    expect(dialog.locator("#agent-detail-title")).to_have_text(paper["results"][1]["model"])
    dialog.get_by_role("button", name="Close agent details").click()
    expect(dialog).not_to_be_visible()
    page.get_by_role("button", name="Path Restoration", exact=True).click()
    expect(page.locator("#reasoning-heading")).to_have_text("Restoration")
    qwen = page.locator("#leaderboard-body tr").filter(has_text="Qwen3.7-Plus")
    expect(qwen).to_contain_text("17.59")
    expect(qwen).to_contain_text("26.58")
    page.get_by_label("Filter by harness").select_option("HermesAgent")
    expect(page.locator("#leaderboard-body tr")).to_have_count(3)
    page.get_by_label("Find an agent or model").fill("telecom")
    expect(page.locator("#leaderboard-body tr")).to_have_count(1)
    expect(page.locator("#leaderboard-body")).to_contain_text("TelecomGPT-R1")
    page.get_by_label("Find an agent or model").fill("__no_result__")
    expect(page.locator("#leaderboard-body")).to_contain_text("No matching")
    page.get_by_label("Find an agent or model").fill("")
    page.get_by_label("Filter by harness").select_option("all")
    page.get_by_role("button", name="Evidence F1").click()
    expect(page.locator("[data-sort-header=evidence]")).to_have_attribute("aria-sort", "descending")
    expect(page.locator("#leaderboard-body tr").first).to_contain_text("GPT-5.5")
    page.get_by_role("button", name="Evidence F1").click()
    expect(page.locator("#leaderboard-body tr").first).to_contain_text("TelecomGPT-R1")
    page.get_by_role("button", name="Copy BibTeX").click()
    expect(page.locator("#copy-feedback")).to_have_text("Citation copied")
    assert "2608.12002" in page.evaluate("navigator.clipboard.readText()")
    with page.expect_download() as download_info:
        page.get_by_role("link", name="Download CSV").click()
    download = download_info.value
    download.save_as(ARTIFACTS / "downloaded-leaderboard.csv")
    assert "17.59" in (ARTIFACTS / "downloaded-leaderboard.csv").read_text()
    page.reload(wait_until="networkidle")
    page.locator("#leaderboard").screenshot(path=str(ARTIFACTS / "leaderboard.png"))
    for width in [390, 768]:
        page.set_viewport_size({"width": width, "height": 844})
        page.goto(preview_url, wait_until="networkidle")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
        page.get_by_role("button", name="Open navigation").click()
        expect(page.locator("#navigation")).to_be_visible()
        page.locator("#navigation").get_by_role("link", name="Leaderboard", exact=True).click()
        expect(page.get_by_role("button", name="Open navigation")).to_have_attribute("aria-expanded", "false")
        page.goto(preview_url, wait_until="networkidle")
        page.screenshot(path=str(ARTIFACTS / f"mobile-{width}.png"), full_page=True)
        page.get_by_role("button", name="View details for Codex + GPT-5.5", exact=True).click()
        expect(dialog).to_be_visible()
        assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth"), width
        assert dialog.locator(".agent-dialog-body").evaluate("el => el.scrollWidth <= el.clientWidth"), width
        dialog.locator(".agent-dialog-body").evaluate("el => el.scrollTop = 0")
        page.screenshot(path=str(ARTIFACTS / f"agent-details-{width}.png"))
        dialog.locator("[data-detail-track=path]").click()
        if details.get("examples", {}).get("path"):
            dialog.get_by_role("button", name="Expand all", exact=True).click()
        assert dialog.locator(".agent-dialog-body").evaluate("el => el.scrollWidth <= el.clientWidth"), width
        page.keyboard.press("Escape")
    with tempfile.TemporaryDirectory() as directory:
        builder.build(Path(directory) / "CTBench_leaderboard", "womengjianhai/CTBench_leaderboard")
        handler = functools.partial(QuietHandler, directory=directory)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            page.set_viewport_size({"width": 1440, "height": 1040})
            page.goto(f"http://127.0.0.1:{server.server_port}/CTBench_leaderboard/", wait_until="networkidle")
            expect(page.locator("#leaderboard-body tr")).to_have_count(5)
            expect(page.locator("#code-resource")).to_have_attribute("href", "https://github.com/netopt-team/ctbench")
            expect(page.locator("#code-description")).to_contain_text("Explore the CTBench repository")
            page.get_by_role("button", name="View details for Codex + GPT-5.5", exact=True).click()
            expect(dialog.locator("#detail-example-kind")).to_have_text("Expert reference trace" if details.get("examples", {}).get("rca") else "Example pending")
            expect(dialog.locator(".efficiency-card").first).to_contain_text("10.81")
            expect(dialog.locator(".efficiency-card").first).to_contain_text("Paper-reported value")
            page.keyboard.press("Escape")
            assert not errors, errors
            assert not bad_responses, bad_responses
        finally:
            page.close()
            server.shutdown()
            server.server_close()
            thread.join()
    browser.close()
    (ARTIFACTS / "checks.json").write_text(json.dumps({"status":"passed","page_errors":errors,"http_errors":bad_responses,"checks":["paper values", "task switching", "harness filter", "search", "empty state", "metric sorting", "citation clipboard", "CSV download", "390px mobile", "768px tablet", "GitHub Pages /CTBench_leaderboard/ prefix", "published repository links", "horizontal figure alignment", "all five agents across RCA/Path", "paper score identity", "paper Table 6 values and reported precision", "trace availability and expert reference provenance", "trace expand/collapse", "keyboard open/Escape/focus return", "agent selector", "390px and 768px dialogs"]}, indent=2), encoding="utf-8")
print(f"Homepage browser checks passed. Artifacts: {ARTIFACTS}")
