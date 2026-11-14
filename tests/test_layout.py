"""Layout regression tests for the e-ink renderer (no network, no secrets).

Run:  python -m pytest tests/ -q
Or:   python tests/test_layout.py   (writes PNGs to tests/output/)
"""
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ---- Stub calendar_config BEFORE direct_renderer imports it (keeps secrets out of git).
stub_config = types.ModuleType("calendar_config")
stub_config.CALENDAR_URL = "https://example.invalid/basic.ics"
stub_config.WEATHER_LATITUDE = 43.4
stub_config.WEATHER_LONGITUDE = -80.5
stub_config.WEATHER_LOCATION_NAME = "Test"
stub_config.WEATHER_UNITS = "celsius"
stub_config.MAX_EVENTS = 6
sys.modules.setdefault("calendar_config", stub_config)

from PIL import Image, ImageDraw  # noqa: E402

from direct_renderer import DirectRenderer  # noqa: E402
from calendar_fetcher import CalendarEvent  # noqa: E402
from weather_fetcher import WeatherData, CurrentWeather, DayForecast  # noqa: E402


def make_weather():
    current = CurrentWeather(temperature=8, weather_code=3, condition="Cloudy")
    forecast = [
        DayForecast(date=datetime(2026, 11, 15), day_name="Sat", temp_max=9, temp_min=3,
                    weather_code=0, condition="Clear"),
        DayForecast(date=datetime(2026, 11, 16), day_name="Sun", temp_max=7, temp_min=2,
                    weather_code=61, condition="Light Rain"),
        DayForecast(date=datetime(2026, 11, 17), day_name="Mon", temp_max=5, temp_min=-1,
                    weather_code=71, condition="Light Snow"),
        DayForecast(date=datetime(2026, 11, 18), day_name="Tue", temp_max=6, temp_min=0,
                    weather_code=2, condition="Partly Cloudy"),
    ]
    return WeatherData(current=current, forecast=forecast, location_name="Test", units="celsius")


def make_events(base, n=6):
    events = []
    for i in range(n):
        d = base + timedelta(days=i // 2, hours=9 + (i % 3) * 3)
        events.append(CalendarEvent(summary=f"Meeting {i + 1}", start_date=d,
                                    end_date=d + timedelta(hours=1)))
    events.append(CalendarEvent(summary="All-day workshop and celebration",
                                start_date=base.replace(hour=0, minute=0),
                                end_date=base.replace(hour=0, minute=0)))
    events.sort(key=lambda e: e.start_date)
    return events[:n]


def make_renderer():
    r = DirectRenderer.__new__(DirectRenderer)
    DirectRenderer._load_fonts(r)
    r.calendar_fetcher = MagicMock()
    r.calendar_fetcher._last_used_cache = False
    r.weather_fetcher = MagicMock()
    return r


def render_case(target_date, events, weather):
    r = make_renderer()
    img = Image.new("L", (r.WIDTH, r.HEIGHT), r.WHITE)
    draw = ImageDraw.Draw(img)
    grid_bottom = r._draw_calendar_grid(draw, target_date, {5, 12, 20}, {1, 2})
    r._draw_chore_wheel(draw, grid_bottom)
    if weather:
        r._draw_weather_panel(draw, weather)
    else:
        r._draw_weather_unavailable(draw)
    r._text_lt(draw, (40, 8), target_date.strftime("%B %Y"), r.font_large)
    r._draw_right_panel(draw, events)
    draw.line([(r.LEFT_PANEL_WIDTH, 0), (r.LEFT_PANEL_WIDTH, r.HEIGHT)],
              fill=r.BLACK, width=r.BORDER_WIDTH)
    img = img.point(lambda p: 255 if p > 128 else 0)
    return img, r, grid_bottom


def test_event_font_scale_capped():
    r = make_renderer()
    assert r._get_event_font_scale() <= 1.25, "event scale must be capped to avoid 32px blowup"
    # With MAX_EVENTS=6: title ~20px, header/time 16px (not 32/24)
    assert r.font_event_title.size <= 21, f"title too big: {r.font_event_title.size}"
    assert r.font_event_header.size <= 16, f"header too big: {r.font_event_header.size}"


def test_six_row_month_does_not_overlap_chore():
    img, r, grid_bottom = render_case(datetime(2026, 8, 15, 12),
                                      make_events(datetime(2026, 8, 15, 9)),
                                      make_weather())
    # 6-row grid with 34px cells: 75 + 6*34 = 279
    assert grid_bottom == 75 + 6 * 34, f"unexpected grid bottom {grid_bottom}"
    assert grid_bottom < 370 - 60, "grid must leave room for chore + weather"


def test_five_row_month_leaves_gap():
    _, _, grid_bottom = render_case(datetime(2026, 11, 14, 12),
                                    make_events(datetime(2026, 11, 14, 9)),
                                    make_weather())
    assert grid_bottom == 75 + 5 * 34


def test_right_panel_uses_lt_anchor():
    # Regression: old code shifted titles up with `title_y = panel_y - bbox[1]`,
    # overlapping headers. New code draws at panel_y with anchor="lt".
    import inspect
    src = inspect.getsource(DirectRenderer._draw_right_panel)
    assert 'anchor="lt"' in src or "anchor='lt'" in src
    assert "title_y = panel_y -" not in src
    assert "time_y = panel_y -" not in src


def test_offline_renders_placeholder():
    img, r, _ = render_case(datetime(2026, 11, 14, 12), [], None)
    assert img.size == (800, 480)


if __name__ == "__main__":
    outdir = Path(__file__).parent / "output"
    outdir.mkdir(exist_ok=True)
    for label, dt in [("aug2026_6row", datetime(2026, 8, 15, 12)),
                      ("nov2026_5row", datetime(2026, 11, 14, 12))]:
        img, _, gb = render_case(dt, make_events(dt.replace(hour=9)), make_weather())
        img.save(outdir / f"{label}.png")
        print(f"{label}: grid_bottom={gb} -> {outdir / (label + '.png')}")
    img, _, _ = render_case(datetime(2026, 11, 14, 12), [], None)
    img.save(outdir / "offline.png")
    print("offline.png written")
    # run assertions
    test_event_font_scale_capped()
    test_six_row_month_does_not_overlap_chore()
    test_five_row_month_leaves_gap()
    test_right_panel_uses_lt_anchor()
    test_offline_renders_placeholder()
    print("all layout checks passed")
