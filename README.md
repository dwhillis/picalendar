# E-Ink Calendar Display

A calendar display optimized for 800×480 e-ink displays, showing the current month and upcoming events from Google Calendar.

## Features

- **Left Panel**: Current month calendar with highlighted event days
- **Right Panel**: List of upcoming events with time, title, and location
- **Weather Forecast**: Current conditions and 4-day forecast
- **High Contrast Design**: Black and white styling optimized for e-ink displays
- **Google Calendar Integration**: Fetches events from Google Calendar

## Setup Instructions

### 1. Make Your Google Calendar Public

1. Open Google Calendar (calendar.google.com)
2. Find the calendar you want to display in the left sidebar
3. Click the three dots next to it → **Settings and sharing**
4. Scroll to **Access permissions** → Check **Make available to public**
5. Scroll to **Integrate calendar** section
6. Copy the **Public address in iCal format** URL
   - It will look like: `https://calendar.google.com/calendar/ical/XXXXX/public/basic.ics`

### 2. Configure the Calendar

Edit `calendar_config.py` and set your calendar URL, weather location, and other settings.

### 3. Raspberry Pi E-Ink Display

For automated display on a Waveshare 7.3" e-ink display connected to Raspberry Pi 5:

```bash
# Install dependencies
pip install -r requirements.txt

# Test display hardware
python3 test_display.py

# Start the display service
python3 main.py

# Or install as systemd service (see SETUP.md)
```

See [SETUP.md](SETUP.md) for complete Raspberry Pi installation and configuration.

## Architecture

The system consists of three main components:

1. **Direct Renderer** (`direct_renderer.py`)
   - Renders the calendar directly to a PIL image buffer
   - Fetches events and weather data via Python
   - Produces a PNG optimized for e-ink

2. **Display Driver** (`display_driver.py`)
   - Communicates with Waveshare display via SPI
   - Controls GPIO pins (reset, data/command, busy)
   - Handles image-to-display conversion

3. **Main Orchestrator** (`main.py`)
   - Manages update cycle
   - Coordinates rendering and display updates
   - Handles error recovery and logging

## Troubleshooting

**Events not showing**:
- Make sure you have future events in your calendar
- Check that your calendar is set to public
- Verify the iCal URL in `calendar_config.py` is correct

**Layout issues**:
- Ensure display resolution is set to 800×480
