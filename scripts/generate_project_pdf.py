from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "index.html"
PDF_PATH = ROOT / "project-overview.pdf"


def main() -> None:
    if not HTML_PATH.exists():
        raise FileNotFoundError(f"HTML source not found: {HTML_PATH}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(HTML_PATH.as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()

    print(f"Generated {PDF_PATH.relative_to(ROOT)} from {HTML_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
