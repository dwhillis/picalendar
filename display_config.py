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
DISPLAY_FLIP = True # Set to True to rotate display 180 degrees

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

UPDATE_SCHEDULE = [
    "0 6 * * *",   # 6:00 AM
    "0 11 * * *",  # 12:00 PM
    "30 16 * * *",  # 6:00 PM
]

# Chore wheel auto-rotation schedule (cron expression)
CHORE_WHEEL_SCHEDULE = "0 0 * * 1"  # Midnight every Monday
STARTUP_DELAY = 1  # Seconds before first update

# Retry configuration
MAX_RENDER_RETRIES = 3
MAX_DISPLAY_RETRIES = 3
RETRY_DELAY = 5  # Seconds between retries

# Behavior settings
CLEAR_ON_STARTUP = False # Clear display on startup
CLEAR_ON_ERROR = True  # Clear display if error occurs
POWER_OFF_ON_SHUTDOWN = True  # Power off display on shutdown

# Timezone (for event display)
TIMEZONE = 'UTC'

# Debug settings
DEBUG_SAVE_RENDERS = True  # Save all rendered PNG files
DEBUG_RENDER_PATH = '/tmp/picalendar_renders'  # Where to save debug renders
