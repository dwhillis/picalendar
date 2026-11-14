"""
Direct Renderer - Render calendar display directly to PIL Image buffer
Bypasses browser rendering to avoid anti-aliasing issues
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
import calendar

from PIL import Image, ImageDraw, ImageFont

from calendar_fetcher import CalendarFetcher, CalendarEvent
from weather_fetcher import WeatherFetcher, WeatherData
import calendar_config as config
import chore_wheel

logger = logging.getLogger(__name__)


class DirectRenderer:
    """Renders calendar display directly to PIL Image"""

    WIDTH = 800
    HEIGHT = 480

    # Layout constants
    LEFT_PANEL_WIDTH = 365
    RIGHT_PANEL_WIDTH = 435
    BORDER_WIDTH = 3

    # Colors (1-bit display: use only BLACK/WHITE for crisp output)
    # GRAY is intentionally unused - it thresholds to black and muddies e-ink.
    WHITE = 255
    BLACK = 0
    GRAY = 128

    def __init__(self):
        """Initialize the direct renderer"""
        self.calendar_fetcher = CalendarFetcher(config.CALENDAR_URL)
        self.weather_fetcher = WeatherFetcher(
            latitude=config.WEATHER_LATITUDE,
            longitude=config.WEATHER_LONGITUDE,
            location_name=config.WEATHER_LOCATION_NAME,
            units=config.WEATHER_UNITS
        )

        # Load fonts
        self._load_fonts()

    def _text_lt(self, draw: ImageDraw.Draw, xy, text: str, font, fill=None):
        """Draw text with left-top anchor for predictable layout."""
        draw.text(xy, text, fill=self.BLACK if fill is None else fill,
                  font=font, anchor="lt")

    def _load_fonts(self):
        """Load fonts for rendering"""
        # Try Terminus first (bitmap font, crisp on e-ink), then fall back to others
        font_paths = [
            "/usr/share/fonts/truetype/terminus/TerminusTTF-4.46.0.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]

        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self.font_tiny = None
        self.font_chore = None
        self.font_icon = None
        self.font_event_header = None
        self.font_event_time = None
        self.font_event_title = None
        loaded_font_path = None

        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    self.font_large = ImageFont.truetype(font_path, 30)
                    self.font_medium = ImageFont.truetype(font_path, 18)
                    self.font_small = ImageFont.truetype(font_path, 14)
                    self.font_tiny = ImageFont.truetype(font_path, 12)
                    self.font_chore = ImageFont.truetype(font_path, 18)
                    loaded_font_path = font_path
                    logger.info(f"Loaded font: {font_path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load font {font_path}: {e}")

        # Try to load emoji font for weather icons
        emoji_paths = [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

        for font_path in emoji_paths:
            if Path(font_path).exists():
                try:
                    self.font_icon = ImageFont.truetype(font_path, 18)
                    break
                except:
                    pass

        # Fallback to default font
        if self.font_large is None:
            logger.warning("No TrueType fonts found, using default bitmap font")
            self.font_large = ImageFont.load_default()
            self.font_medium = self.font_large
            self.font_small = self.font_large
            self.font_tiny = self.font_large
            self.font_chore = self.font_large
            self.font_icon = self.font_large

        event_font_scale = self._get_event_font_scale()
        self.event_row_padding = max(3, int(round(4 * event_font_scale)))
        self.event_row_spacing = max(4, int(round(6 * event_font_scale)))
        self.event_header_spacing = max(2, int(round(4 * event_font_scale)))
        self.font_event_header = self.font_tiny
        self.font_event_time = self.font_tiny
        self.font_event_title = self.font_small

        if loaded_font_path:
            try:
                self.font_event_header = ImageFont.truetype(
                    loaded_font_path,
                    max(14, int(round(13 * event_font_scale)))
                )
                self.font_event_time = ImageFont.truetype(
                    loaded_font_path,
                    max(14, int(round(13 * event_font_scale)))
                )
                self.font_event_title = ImageFont.truetype(
                    loaded_font_path,
                    max(18, int(round(16 * event_font_scale)))
                )
            except Exception as e:
                logger.warning(f"Failed to load scaled event fonts: {e}")

    def _get_event_font_scale(self) -> float:
        """Scale event text, capped so text stays readable and fits."""
        baseline_events = 8
        if config.MAX_EVENTS <= 0:
            return 1.0
        return max(1.0, min(1.25, baseline_events / config.MAX_EVENTS))

    def render(self) -> Image.Image:
        """Render the complete calendar display

        Returns:
            PIL Image in mode 'L' (grayscale)
        """
        # Create image in grayscale mode
        img = Image.new('L', (self.WIDTH, self.HEIGHT), self.WHITE)
        draw = ImageDraw.Draw(img)

        # Fetch data (fetchers fall back to on-disk cache on network failure)
        events = self.calendar_fetcher.fetch_events(max_events=config.MAX_EVENTS)
        weather = self.weather_fetcher.fetch_weather()

        # Get event days for current month and next month (including past events)
        now = datetime.now()
        event_days = self.calendar_fetcher.get_event_dates_for_month(now.year, now.month)

        # Get next month event days for visible trailing days
        if now.month == 12:
            next_month_event_days = self.calendar_fetcher.get_event_dates_for_month(now.year + 1, 1)
        else:
            next_month_event_days = self.calendar_fetcher.get_event_dates_for_month(now.year, now.month + 1)

        # Draw panels
        self._draw_left_panel(draw, now, event_days, next_month_event_days, weather)
        self._draw_right_panel(draw, events)

        # Draw vertical separator
        draw.line(
            [(self.LEFT_PANEL_WIDTH, 0), (self.LEFT_PANEL_WIDTH, self.HEIGHT)],
            fill=self.BLACK,
            width=self.BORDER_WIDTH
        )

        return img

    def _get_event_days(self, events: List[CalendarEvent], year: int, month: int) -> Set[int]:
        """Get set of days in month that have events"""
        event_days = set()
        for event in events:
            if event.start_date.year == year and event.start_date.month == month:
                event_days.add(event.start_date.day)
        return event_days

    def _draw_left_panel(self, draw: ImageDraw.Draw, now: datetime,
                         event_days: Set[int], next_month_event_days: Set[int],
                         weather: Optional[WeatherData]):
        """Draw the left panel with calendar and weather"""
        # Month header
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        header_text = f"{month_names[now.month - 1]} {now.year}"

        # Center the header with predictable lt anchor
        bbox = draw.textbbox((0, 0), header_text, font=self.font_large, anchor="lt")
        text_width = bbox[2] - bbox[0]
        header_x = (self.LEFT_PANEL_WIDTH - text_width) // 2
        self._text_lt(draw, (header_x, 8), header_text, self.font_large)

        # Calendar grid (returns bottom y so widgets below can flow)
        grid_bottom = self._draw_calendar_grid(draw, now, event_days, next_month_event_days)

        # Chore wheel widget (dynamically placed below grid)
        self._draw_chore_wheel(draw, grid_bottom)

        # Weather panel (always drawn; placeholder when offline)
        if weather:
            self._draw_weather_panel(draw, weather)
        else:
            self._draw_weather_unavailable(draw)

    def _draw_calendar_grid(self, draw: ImageDraw.Draw, now: datetime,
                            event_days: Set[int], next_month_event_days: Set[int]) -> int:
        """Draw the monthly calendar grid. Returns bottom y of grid."""
        # Grid position - cell_height 34 fits 6 rows (204px) without hitting chore wheel
        grid_x = 15
        grid_y = 50
        cell_width = 47
        cell_height = 34

        # Day headers
        day_headers = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        for i, day in enumerate(day_headers):
            x = grid_x + i * cell_width
            bbox = draw.textbbox((0, 0), day, font=self.font_small, anchor="lt")
            tw = bbox[2] - bbox[0]
            self._text_lt(draw, (x + (cell_width - tw) // 2, grid_y), day, self.font_small)

        # Underline day headers
        draw.line(
            [(grid_x, grid_y + 18), (grid_x + 7 * cell_width, grid_y + 18)],
            fill=self.BLACK,
            width=2
        )

        grid_y += 25

        # Get calendar data
        year, month = now.year, now.month
        today = now.day

        # First day of month (0 = Monday, but we want Sunday = 0)
        first_weekday = (calendar.monthrange(year, month)[0] + 1) % 7
        days_in_month = calendar.monthrange(year, month)[1]
        days_in_prev_month = calendar.monthrange(year, month - 1 if month > 1 else 12)[1]

        # Draw calendar cells
        row = 0
        col = 0

        # Previous month days (no border: crisp + distinct on 1-bit)
        for i in range(first_weekday):
            day = days_in_prev_month - first_weekday + i + 1
            self._draw_calendar_cell(
                draw, grid_x + col * cell_width, grid_y + row * cell_height,
                cell_width, cell_height, day, is_other_month=True
            )
            col += 1

        # Current month days
        for day in range(1, days_in_month + 1):
            is_today = (day == today)
            has_event = (day in event_days)

            self._draw_calendar_cell(
                draw, grid_x + col * cell_width, grid_y + row * cell_height,
                cell_width, cell_height, day, is_today=is_today, has_event=has_event
            )

            col += 1
            if col >= 7:
                col = 0
                row += 1

        # Next month days (no border)
        next_day = 1
        while col > 0 and col < 7:
            has_event = (next_day in next_month_event_days)
            self._draw_calendar_cell(
                draw, grid_x + col * cell_width, grid_y + row * cell_height,
                cell_width, cell_height, next_day, is_other_month=True, has_event=has_event
            )
            col += 1
            next_day += 1

        # Compute rows used and bottom edge
        import math
        rows_used = math.ceil((first_weekday + days_in_month) / 7)
        return grid_y + rows_used * cell_height

    def _draw_calendar_cell(self, draw: ImageDraw.Draw, x: int, y: int,
                            width: int, height: int, day: int,
                            is_today: bool = False, has_event: bool = False,
                            is_other_month: bool = False):
        """Draw a single calendar cell"""
        if not is_other_month:
            draw.rectangle(
                [(x + 1, y + 1), (x + width - 1, y + height - 1)],
                outline=self.BLACK,
                width=1
            )

        # Background for today
        if is_today:
            draw.rectangle(
                [(x + 2, y + 2), (x + width - 2, y + height - 2)],
                fill=self.BLACK
            )

        # Day number (lt anchor: y is exact top)
        day_text = str(day)
        bbox = draw.textbbox((0, 0), day_text, font=self.font_medium, anchor="lt")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2

        text_color = self.WHITE if is_today else self.BLACK

        self._text_lt(draw, (text_x, text_y), day_text, self.font_medium, fill=text_color)

        # Event indicator: single bottom-center dot (crisp, low ink)
        if has_event:
            cx = x + width // 2
            dot_color = self.WHITE if is_today else self.BLACK
            draw.rectangle(
                [(cx - 4, y + height - 6), (cx + 4, y + height - 3)],
                fill=dot_color
            )

    def _draw_weather_unavailable(self, draw: ImageDraw.Draw):
        """Placeholder so layout does not collapse when offline."""
        panel_y = 370
        panel_x = 15
        panel_width = self.LEFT_PANEL_WIDTH - 30
        draw.line(
            [(panel_x, panel_y), (panel_x + panel_width, panel_y)],
            fill=self.BLACK,
            width=2
        )
        self._text_lt(draw, (panel_x, panel_y + 8),
                      "Weather unavailable (offline)", self.font_small)

    def _draw_weather_panel(self, draw: ImageDraw.Draw, weather: WeatherData):
        """Draw the weather panel at bottom of left panel"""
        panel_y = 370
        panel_x = 15
        panel_width = self.LEFT_PANEL_WIDTH - 30

        # Top border
        draw.line(
            [(panel_x, panel_y), (panel_x + panel_width, panel_y)],
            fill=self.BLACK,
            width=2
        )

        panel_y += 8

        # Current weather
        unit_symbol = 'C' if weather.units == 'celsius' else 'F'
        temp_text = f"{weather.current.temperature}{unit_symbol}"

        # Temperature (large)
        self._text_lt(draw, (panel_x, panel_y), temp_text, self.font_large)

        # Condition (truncate to fit panel instead of overflowing)
        bbox = draw.textbbox((0, 0), temp_text, font=self.font_large, anchor="lt")
        condition_x = panel_x + (bbox[2] - bbox[0]) + 10
        condition = weather.current.condition
        max_cond_w = panel_x + panel_width - condition_x
        cb = draw.textbbox((0, 0), condition, font=self.font_medium, anchor="lt")
        while cb[2] - cb[0] > max_cond_w and len(condition) > 3:
            condition = condition[:-4] + "..."
            cb = draw.textbbox((0, 0), condition, font=self.font_medium, anchor="lt")

        self._text_lt(draw, (condition_x, panel_y + 6), condition, self.font_medium)

        # Separator line
        panel_y += 34
        draw.line(
            [(panel_x, panel_y), (panel_x + panel_width, panel_y)],
            fill=self.BLACK,
            width=1
        )

        panel_y += 8

        # Forecast days
        day_width = panel_width // 4
        for i, day in enumerate(weather.forecast):
            day_x = panel_x + i * day_width + day_width // 2

            # Day name
            bbox = draw.textbbox((0, 0), day.day_name, font=self.font_small, anchor="lt")
            text_width = bbox[2] - bbox[0]
            self._text_lt(draw, (day_x - text_width // 2, panel_y), day.day_name,
                          self.font_small)

            # Weather icon (outline style for crisp e-ink)
            self._draw_weather_icon(draw, day_x, panel_y + 24, day.weather_code)

            # Temperature range
            temp_text = f"{day.temp_max}/{day.temp_min}"
            bbox = draw.textbbox((0, 0), temp_text, font=self.font_tiny, anchor="lt")
            text_width = bbox[2] - bbox[0]
            self._text_lt(draw, (day_x - text_width // 2, panel_y + 40), temp_text,
                          self.font_tiny)

    def _draw_chore_wheel(self, draw: ImageDraw.Draw, grid_bottom: int = 0):
        """Draw the chore wheel below the calendar grid (dynamic y)."""
        panel_x = 15
        panel_width = self.LEFT_PANEL_WIDTH - 30

        # Flow below grid with margin; never overlap grid, never hit weather (370)
        chore_top = max(grid_bottom + 8 if grid_bottom else 286, 240)
        # Reserve ~60px for icons+names; clamp so bottom stays above weather border
        if chore_top + 60 > 360:
            chore_top = 360 - 60
        panel_y = chore_top

        names = chore_wheel.get_names()
        rotation = chore_wheel.get_rotation()

        # Ensure we have at least 3 names (pad with ? if needed)
        while len(names) < 3:
            names.append('?')

        # Categories: Movie, Food, Games
        categories = [
            ('Movie', self._draw_movie_icon),
            ('Food', self._draw_food_icon),
            ('Games', self._draw_games_icon),
        ]

        col_width = panel_width // 3

        for i, (label, draw_icon) in enumerate(categories):
            col_x = panel_x + i * col_width + col_width // 2

            # Draw icon
            draw_icon(draw, col_x, panel_y + 16)

            # Get rotated name for this category
            name_idx = (i + rotation) % len(names)
            name = names[name_idx]

            # Truncate name if too long
            max_name_width = col_width - 8
            bbox = draw.textbbox((0, 0), name, font=self.font_chore, anchor="lt")
            while bbox[2] - bbox[0] > max_name_width and len(name) > 1:
                name = name[:-1]
                bbox = draw.textbbox((0, 0), name, font=self.font_chore, anchor="lt")

            # Draw name centered below icon
            text_width = bbox[2] - bbox[0]
            self._text_lt(draw, (col_x - text_width // 2, panel_y + 42), name,
                          self.font_chore)

    def _draw_movie_icon(self, draw: ImageDraw.Draw, cx: int, cy: int):
        """Draw an open clapperboard icon"""
        w, h = 26, 18
        # Main board body
        board_top = cy - h//2 + 7
        draw.rectangle([(cx - w//2, board_top), (cx + w//2, cy + h//2 + 5)],
                       outline=self.BLACK, fill=self.WHITE, width=2)
        # Open clapper (angled up from hinge point at top-left of board)
        hinge_x = cx - w//2
        hinge_y = board_top
        clapper_end_x = cx + w//2
        clapper_end_y = cy - h//2 - 5
        # Draw clapper as angled rectangle
        draw.polygon([
            (hinge_x, hinge_y),
            (hinge_x, hinge_y - 5),
            (clapper_end_x, clapper_end_y - 5),
            (clapper_end_x, clapper_end_y)
        ], outline=self.BLACK, fill=self.WHITE)
        # Diagonal stripes on clapper
        for i in range(4):
            t = (i + 1) / 5
            x1 = hinge_x + t * (clapper_end_x - hinge_x)
            y1 = hinge_y + t * (clapper_end_y - hinge_y)
            y1_top = (hinge_y - 5) + t * ((clapper_end_y - 5) - (hinge_y - 5))
            draw.line([(x1, y1_top), (x1, y1)], fill=self.BLACK, width=2)


    def _draw_food_icon(self, draw: ImageDraw.Draw, cx: int, cy: int):
        """Draw a fork/knife icon"""
        # Fork (left)
        draw.line([(cx - 4, cy - 13), (cx - 4, cy - 5)], fill=self.BLACK, width=2)
        draw.line([(cx - 7, cy - 13), (cx - 7, cy - 5)], fill=self.BLACK, width=2)
        draw.line([(cx - 10, cy - 13), (cx - 10, cy - 5)], fill=self.BLACK, width=2)

        draw.line([(cx - 7, cy - 5), (cx - 7, cy + 13)], fill=self.BLACK, width=2)

        # Knife (right)
        draw.line([(cx + 8, cy - 13), (cx + 8, cy + 13)], fill=self.BLACK, width=2)
        draw.polygon([
            (cx + 5, cy - 13),
            (cx + 8, cy - 13),
            (cx + 8, cy + 2),
            (cx + 5, cy - 3)
        ], outline=self.BLACK)

    def _draw_games_icon(self, draw: ImageDraw.Draw, cx: int, cy: int):
        """Draw a dice/game icon"""
        # Dice outline
        size = 22
        draw.rectangle([(cx - size//2, cy - size//2), (cx + size//2, cy + size//2)],
                       outline=self.BLACK, width=2)
        # Dots (showing 3)
        dot_r = 3
        draw.ellipse([(cx - dot_r, cy - dot_r), (cx + dot_r, cy + dot_r)], fill=self.BLACK)
        draw.ellipse([(cx + 6 - dot_r, cy - 6 - dot_r), (cx + 6 + dot_r, cy - 6 + dot_r)], fill=self.BLACK)
        draw.ellipse([(cx - 6 - dot_r, cy + 6 - dot_r), (cx - 6 + dot_r, cy + 6 + dot_r)], fill=self.BLACK)

    def _draw_weather_icon(self, draw: ImageDraw.Draw, cx: int, cy: int, code: int):
        """Outline-style weather icons for crisp 1-bit e-ink."""
        if code == 0 or code == 1:
            # Sun - outline circle with rays
            r = 5
            draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=self.BLACK, width=2)
            import math
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x1 = cx + int((r + 2) * math.cos(rad))
                y1 = cy + int((r + 2) * math.sin(rad))
                x2 = cx + int((r + 4) * math.cos(rad))
                y2 = cy + int((r + 4) * math.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=self.BLACK, width=1)

        elif code == 2:
            # Partly cloudy - small outline sun + outline cloud
            r = 4
            draw.ellipse([(cx - 2 - r, cy - 4 - r), (cx - 2 + r, cy - 4 + r)], outline=self.BLACK, width=1)
            draw.ellipse([(cx - 6, cy - 2), (cx + 2, cy + 6)], outline=self.BLACK, width=1)
            draw.ellipse([(cx - 2, cy - 4), (cx + 8, cy + 6)], outline=self.BLACK, width=1)

        elif code == 3:
            # Cloudy - outline cloud shape
            draw.ellipse([(cx - 8, cy - 2), (cx, cy + 6)], outline=self.BLACK, width=1)
            draw.ellipse([(cx - 4, cy - 6), (cx + 6, cy + 4)], outline=self.BLACK, width=1)
            draw.ellipse([(cx - 2, cy - 2), (cx + 8, cy + 6)], outline=self.BLACK, width=1)

        elif code in (45, 48):
            # Fog - horizontal lines
            for i in range(-2, 3):
                y = cy + i * 3
                draw.line([(cx - 8, y), (cx + 8, y)], fill=self.BLACK, width=1)

        elif 51 <= code <= 55 or 80 <= code <= 82:
            # Drizzle/showers - outline cloud + thin drops
            draw.ellipse([(cx - 6, cy - 6), (cx, cy)], outline=self.BLACK, width=1)
            draw.ellipse([(cx - 2, cy - 6), (cx + 6, cy)], outline=self.BLACK, width=1)
            draw.line([(cx - 4, cy + 2), (cx - 4, cy + 5)], fill=self.BLACK, width=1)
            draw.line([(cx + 2, cy + 3), (cx + 2, cy + 6)], fill=self.BLACK, width=1)

        elif 61 <= code <= 65:
            # Rain - outline cloud + drops
            draw.ellipse([(cx - 6, cy - 6), (cx, cy)], outline=self.BLACK, width=1)
            draw.ellipse([(cx - 2, cy - 6), (cx + 6, cy)], outline=self.BLACK, width=1)
            draw.line([(cx - 5, cy + 2), (cx - 5, cy + 6)], fill=self.BLACK, width=1)
            draw.line([(cx, cy + 2), (cx, cy + 6)], fill=self.BLACK, width=1)
            draw.line([(cx + 4, cy + 2), (cx + 4, cy + 6)], fill=self.BLACK, width=1)

        elif 71 <= code <= 77 or 85 <= code <= 86:
            # Snow - snowflake pattern
            draw.line([(cx, cy - 6), (cx, cy + 6)], fill=self.BLACK, width=1)
            draw.line([(cx - 6, cy), (cx + 6, cy)], fill=self.BLACK, width=1)
            draw.line([(cx - 4, cy - 4), (cx + 4, cy + 4)], fill=self.BLACK, width=1)
            draw.line([(cx - 4, cy + 4), (cx + 4, cy - 4)], fill=self.BLACK, width=1)

        elif 95 <= code <= 99:
            # Thunderstorm - outline bolt
            points = [
                (cx - 2, cy - 6),
                (cx + 4, cy - 6),
                (cx, cy - 1),
                (cx + 4, cy - 1),
                (cx - 4, cy + 6),
                (cx, cy),
                (cx - 4, cy),
            ]
            draw.polygon(points, outline=self.BLACK)

        else:
            # Unknown - question mark
            self._text_lt(draw, (cx - 4, cy - 6), "?", self.font_small)

    def _draw_right_panel(self, draw: ImageDraw.Draw, events: List[CalendarEvent]):
        """Draw the right panel with upcoming events (lt-anchor layout)."""
        panel_x = self.LEFT_PANEL_WIDTH + 15
        panel_y = 10
        panel_width = self.RIGHT_PANEL_WIDTH - 30

        used_cache = getattr(self.calendar_fetcher, '_last_used_cache', False) is True

        if not events:
            self._text_lt(draw, (panel_x, panel_y), "No upcoming events",
                          self.font_event_header)
            if used_cache:
                self._text_lt(draw, (panel_x, panel_y + 22),
                              "(offline - no cache)", self.font_event_time)
            self._draw_offline_footer(draw, used_cache)
            return

        # Group events by date
        current_date = None

        for event in events:
            event_date = event.start_date.date()

            # Date separator
            if event_date != current_date:
                current_date = event_date
                date_label = self._format_date_label(event.start_date)

                if panel_y > 10:
                    panel_y += self.event_header_spacing

                date_bbox = draw.textbbox((0, 0), date_label,
                                          font=self.font_event_header, anchor="lt")
                date_height = date_bbox[3] - date_bbox[1]
                if panel_y + date_height > self.HEIGHT - 30:
                    break

                self._text_lt(draw, (panel_x, panel_y), date_label, self.font_event_header)
                panel_y += date_height + 2

                # Underline date header
                draw.line(
                    [(panel_x, panel_y), (panel_x + panel_width, panel_y)],
                    fill=self.BLACK,
                    width=1
                )

                panel_y += self.event_header_spacing

            time_text = self._format_time(event)
            time_width = 0
            time_height = 0
            if time_text:
                time_bbox = draw.textbbox((0, 0), time_text,
                                          font=self.font_event_time, anchor="lt")
                time_width = time_bbox[2] - time_bbox[0]
                time_height = time_bbox[3] - time_bbox[1]

            title_bbox_ref = draw.textbbox((0, 0), "Ag",
                                           font=self.font_event_title, anchor="lt")
            title_height = title_bbox_ref[3] - title_bbox_ref[1]
            text_height = max(time_height, title_height)

            line_height = text_height + self.event_row_padding
            if panel_y + line_height > self.HEIGHT - 30:
                break

            line_x = panel_x + 2
            title_x = line_x
            if time_text:
                self._text_lt(draw, (line_x, panel_y), time_text, self.font_event_time)
                title_x += time_width + 10

            # Title (truncate if needed)
            max_title_width = panel_width - (title_x - panel_x)

            title = event.summary
            title_bbox = draw.textbbox((0, 0), title,
                                       font=self.font_event_title, anchor="lt")
            while title_bbox[2] - title_bbox[0] > max_title_width and len(title) > 3:
                title = title[:-4] + "..."
                title_bbox = draw.textbbox((0, 0), title,
                                           font=self.font_event_title, anchor="lt")

            self._text_lt(draw, (title_x, panel_y), title, self.font_event_title)

            panel_y += line_height + self.event_row_spacing

        self._draw_offline_footer(draw, used_cache)

    def _draw_offline_footer(self, draw: ImageDraw.Draw, used_cache: bool):
        """Small status line at bottom of right panel."""
        if not used_cache:
            return
        footer = "offline - showing cached"
        bbox = draw.textbbox((0, 0), footer, font=self.font_tiny, anchor="lt")
        fx = self.LEFT_PANEL_WIDTH + 15
        fy = self.HEIGHT - (bbox[3] - bbox[1]) - 6
        self._text_lt(draw, (fx, fy), footer, self.font_tiny)

    def _format_date_label(self, dt: datetime) -> str:
        """Format date as a compact label for the event list."""
        today = datetime.now().date()
        event_date = dt.date()

        if event_date == today:
            return "TODAY"
        elif event_date == today + timedelta(days=1):
            return "TOMORROW"
        else:
            days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
            weekday = days[(dt.weekday() + 1) % 7]  # Convert Monday=0 to Sunday=0
            return f"{weekday} {dt.day}"

    def _format_time(self, event: CalendarEvent) -> str:
        """Format time as a compact token for the event list."""
        if event.is_all_day:
            return ""

        hour = event.start_date.hour
        minute = event.start_date.minute
        ampm = 'p' if hour >= 12 else 'a'

        hour = hour % 12
        if hour == 0:
            hour = 12

        if minute == 0:
            return f"{hour}{ampm}"

        return f"{hour}:{minute:02d}{ampm}"

    def render_to_png(self, output_path: Optional[str] = None) -> str:
        """Render calendar and save to PNG file

        Args:
            output_path: Path to save PNG. If None, uses temp file.

        Returns:
            Path to rendered PNG file
        """
        import tempfile
        import os

        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)

        img = self.render()

        # Convert to 1-bit for crisp e-ink display
        img = img.point(lambda p: 255 if p > 128 else 0)

        img.save(output_path, 'PNG')
        logger.info(f"Rendered to {output_path}")

        return output_path


def render_calendar_direct(output_path: Optional[str] = None) -> str:
    """Convenience function to render calendar in one call

    Args:
        output_path: Output PNG path (defaults to temp file)

    Returns:
        Path to rendered PNG
    """
    renderer = DirectRenderer()
    return renderer.render_to_png(output_path)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    output = render_calendar_direct('/tmp/calendar_direct.png')
    print(f"Rendered to: {output}")
