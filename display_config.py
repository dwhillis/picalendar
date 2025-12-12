"""
Configuration for e-ink display system
"""

from pathlib import Path
import logging

# Logging configuration
LOG_LEVEL = logging.INFO
LOG_FILE = '/var/log/picalendar.log'

# Display settings
DISPLAY_ENABLED = True  # Set to False for testing without display hardware
DISPLAY_SIMULATE = False  # Set to True to simulate display without GPIO

# Display hardware configuration
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
GPIO_PIN_RST = 17
GPIO_PIN_DC = 25
GPIO_PIN_CS = 8
GPIO_PIN_BUSY = 24
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 4000000  # 4 MHz

# Web renderer settings
WEB_ROOT = Path(__file__).parent  # Directory containing index.html
HTTP_PORT = 8000
RENDER_TIMEOUT = 30  # seconds
RENDER_OPTIMIZE = True  # Apply dithering for e-ink

# Update schedule
UPDATE_INTERVAL = 1800  # Seconds (30 minutes)
STARTUP_DELAY = 5  # Seconds before first update
FORCE_FULL_REFRESH = 3600  # Full refresh every hour (seconds)

# Retry configuration
MAX_RENDER_RETRIES = 3
MAX_DISPLAY_RETRIES = 3
RETRY_DELAY = 5  # Seconds between retries

# Behavior settings
CLEAR_ON_STARTUP = True  # Clear display on startup
CLEAR_ON_ERROR = True  # Clear display if error occurs
POWER_OFF_ON_SHUTDOWN = True  # Power off display on shutdown

# Timezone (for event display)
TIMEZONE = 'UTC'

# Debug settings
DEBUG_SAVE_RENDERS = False  # Save all rendered PNG files
DEBUG_RENDER_PATH = '/tmp/picalendar_renders'  # Where to save debug renders
