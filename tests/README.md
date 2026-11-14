# PiCalendar render tests

Visual + assertion tests for the 800x480 e-ink layout. No network, no secrets.

```bash
python -m pytest tests/ -q
python tests/test_layout.py   # also writes PNGs to tests/output/
```

What it covers:
- 6-row months (e.g. Aug 2026) end at y=279 with 34px cells and never hit the chore wheel.
- Event font scale capped at 1.25x (header/time 16px, title ~20px with `MAX_EVENTS=6`).
- Right panel uses `anchor="lt"` (no `-bbox[1]` shifts that overlapped headers).
- Offline renders a weather placeholder instead of collapsing the layout.
