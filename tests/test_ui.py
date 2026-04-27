import threading
import time
from typing import Any

import httpx
import pytest
import uvicorn

from app.services.calculator import Calculator

try:
    from playwright.sync_api import Page, expect

    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False

pytestmark = pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="playwright not installed")

# Provide minimal placeholders so annotations / references don't fail when plugin absent
if not HAS_PLAYWRIGHT:

    class Page:  # type: ignore
        pass

    def expect(locator: Any) -> Any:  # type: ignore
        class Dummy:
            def to_have_value(self: Any, *a: Any, **k: Any) -> Any:
                return None

            def to_contain_text(self: Any, *a: Any, **k: Any) -> Any:
                return None

        return Dummy()


@pytest.fixture(scope="session", autouse=True)
def live_server() -> Any:
    import socket

    # Find a free port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()

    # Start uvicorn in a background thread to avoid external shell wrappers
    def run_server() -> Any:
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"

    # Wait until server is up
    for _ in range(50):
        try:
            res = httpx.get(url)
            if res.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError("Failed to start test server")

    yield url
    # server thread is daemon; it will exit when tests complete


def test_calculator_basic_addition(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_text("2", exact=True).click()
    page.get_by_text("+", exact=True).click()
    page.get_by_text("3", exact=True).click()
    page.get_by_text("=", exact=True).click()

    # Result is replaced in the expression input
    expect(page.locator("#expression")).to_have_value("5")
    expect(page.locator("#result")).to_have_text("")


def test_calculator_divide_by_zero(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_text("5", exact=True).click()
    page.get_by_text("÷", exact=True).click()
    page.get_by_text("0", exact=True).click()
    page.get_by_text("=", exact=True).click()

    # Error should appear in #result div
    expect(page.locator("#result")).to_contain_text("0で割ることはできません")


def test_calculator_parenthesized_repeating_decimal_is_rejected(
    page: Page, live_server: str
) -> None:
    page.goto(live_server)
    page.locator("#expression").fill("0.(3)")
    page.get_by_text("=", exact=True).click()

    expect(page.locator("#result")).to_contain_text("計算式が正しくありません")


def test_ac_button_clears_display(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_text("9", exact=True).click()
    expect(page.locator("#expression")).to_have_value("9")

    page.get_by_text("AC", exact=True).click()
    expect(page.locator("#expression")).to_have_value("")


def test_fraction_bar_tracks_denominator_width(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.get_by_text("1", exact=True).click()
    page.get_by_text("÷", exact=True).click()
    page.get_by_text("2", exact=True).click()
    page.get_by_text("6", exact=True).click()
    page.get_by_text("0", exact=True).click()
    page.get_by_text("1", exact=True).click()
    page.get_by_text("=", exact=True).click()

    expect(page.locator(".fraction .den")).to_be_visible()
    page.wait_for_function(
        """
        () => {
          const den = document.querySelector('.fraction .den');
          const bar = document.querySelector('.fraction .bar');
          if (!den || !bar) return false;
          const denWidth = den.getBoundingClientRect().width;
          const barWidth = bar.getBoundingClientRect().width;
          return Math.abs(denWidth - barWidth) <= 2;
        }
        """
    )


def test_calculator_can_continue_from_repeating_decimal_result(
    page: Page, live_server: str
) -> None:
    page.goto(live_server)
    page.get_by_text("1", exact=True).click()
    page.get_by_text("÷", exact=True).click()
    page.get_by_text("3", exact=True).click()
    page.get_by_text("2", exact=True).click()
    page.get_by_text("6", exact=True).click()
    page.get_by_text("7", exact=True).click()
    page.get_by_text("=", exact=True).click()

    expect(page.locator("#expression")).not_to_have_value("1/3267")
    assert page.locator("#expression").input_value().startswith("0.")

    page.get_by_text("×", exact=True).click()
    page.get_by_text("2", exact=True).click()
    page.get_by_text("=", exact=True).click()

    expect(page.locator("#result")).to_have_text("")
    assert page.locator("#expression").input_value() != "計算式が正しくありません"


def test_calculator_can_continue_from_repeating_decimal_result_with_addition(
    page: Page, live_server: str
) -> None:
    page.goto(live_server)
    page.get_by_text("1", exact=True).click()
    page.get_by_text("÷", exact=True).click()
    page.get_by_text("3", exact=True).click()
    page.get_by_text("2", exact=True).click()
    page.get_by_text("6", exact=True).click()
    page.get_by_text("7", exact=True).click()
    page.get_by_text("=", exact=True).click()

    expected = Calculator().format_result(Calculator().safe_eval("2 + 1/3267"), False)

    page.get_by_text("+", exact=True).click()
    page.get_by_text("2", exact=True).click()
    page.get_by_text("=", exact=True).click()

    expect(page.locator("#expression")).to_have_value(expected)
    expect(page.locator("#result")).to_have_text("")
