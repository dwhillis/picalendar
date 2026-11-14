"""
Calendar and Weather Configuration - EXAMPLE
Copy to calendar_config.py and fill in your values.
calendar_config.py is gitignored so secrets never land in git.
"""

# Google Calendar Configuration (public iCal URL)
# Google Calendar -> Settings -> Integrate calendar -> Public address in iCal format
CALENDAR_URL = 'https://calendar.google.com/calendar/ical/YOUR_CALENDAR_ID/public/basic.ics'

# Weather Configuration (Open-Meteo, no key needed)
WEATHER_LATITUDE = 43.4086299
WEATHER_LONGITUDE = -80.5045712
WEATHER_LOCATION_NAME = 'Kitchener, ON'
WEATHER_UNITS = 'celsius'  # 'celsius' or 'fahrenheit'

# Display Configuration
# 6-8 events keeps text at 1.0-1.25x scale (header/time 16px, title ~20px).
# Lower values (e.g. 4) scale text up to 2x and truncate/overflow the 480px panel.
MAX_EVENTS = 6

DISPLAY_FLIP = True

# Chore wheel state (names + rotation) is stored in chore_wheel_data.json
