import subprocess
import time

import httpx
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session", autouse=True)
def live_server():
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = "http://127.0.0.1:8000"

    # Wait until server is up
    for _ in range(50):
        try:
            res = httpx.get(url)
            if res.status_code == 200:
                break
        except httpx.ConnectError:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("Failed to start test server")

    yield url
    proc.terminate()
    proc.wait()


def test_calculator_basic_addition(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_text("2", exact=True).click()
    page.get_by_text("+", exact=True).click()
    page.get_by_text("3", exact=True).click()
    page.get_by_text("=", exact=True).click()

    # Result is replaced in the expression input
    expect(page.locator("#expression")).to_have_value("5")


def test_calculator_divide_by_zero(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_text("5", exact=True).click()
    page.get_by_text("÷", exact=True).click()
    page.get_by_text("0", exact=True).click()
    page.get_by_text("=", exact=True).click()

    # Error should appear in #result div
    expect(page.locator("#result")).to_contain_text("0で割ることはできません")


def test_ac_button_clears_display(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_text("9", exact=True).click()
    expect(page.locator("#expression")).to_have_value("9")

    page.get_by_text("AC", exact=True).click()
    expect(page.locator("#expression")).to_have_value("")
