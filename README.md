# E-Ink Calendar Display

A web-based calendar display optimized for 800×480 e-ink displays, showing the current month and upcoming events from Google Calendar.

## Features

- **Left Panel**: Current month calendar with highlighted event days
- **Right Panel**: List of next 7-10 upcoming events with time, title, and location
- **High Contrast Design**: Black and white styling optimized for e-ink displays
- **Google Calendar Integration**: Fetches events from public Google Calendar

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

1. Open `calendar.js` in a text editor
2. Find the `CALENDAR_CONFIG` section at the top
3. Replace `YOUR_CALENDAR_URL_HERE` with your public iCal URL:

```javascript
const CALENDAR_CONFIG = {
    calendarUrl: 'https://calendar.google.com/calendar/ical/YOUR_CALENDAR_ID/public/basic.ics',
    corsProxy: 'https://corsproxy.io/?'
};
```

### 3. Test the Display

Open `index.html` in a web browser. You should see:
- Current month calendar on the left
- Your upcoming events on the right

### 4. Raspberry Pi E-Ink Display (Optional)

For automated display on a Waveshare 7.3" e-ink display connected to Raspberry Pi 5:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python3 test_render.py    # Test web rendering
python3 test_display.py   # Test display hardware

# Start the display service
python3 main.py

# Or install as systemd service (see SETUP.md)
```

See [SETUP.md](SETUP.md) for complete Raspberry Pi installation and configuration.

## Architecture

The system consists of three main components:

1. **Web Calendar** (`index.html`, `calendar.js`, `style.css`)
   - Browser-based calendar display
   - Fetches events from Google Calendar
   - Renders at 800×480 resolution

2. **Web Renderer** (`web_renderer.py`)
   - Runs local HTTP server
   - Uses Playwright/Selenium to render webpage headlessly
   - Converts to PNG with optional dithering for e-ink

3. **Display Driver** (`display_driver.py`)
   - Communicates with Waveshare display via SPI
   - Controls GPIO pins (reset, data/command, busy)
   - Handles image-to-display conversion

4. **Main Orchestrator** (`main.py`)
   - Manages update cycle
   - Coordinates rendering and display updates
   - Handles error recovery and logging

## Customization

### Change Event Count

In `calendar.js`, find this line and adjust the number:
```javascript
.slice(0, 10); // Get next 10 events
```

### Adjust Styling

Edit `style.css` to modify:
- Font sizes
- Border thickness
- Spacing and padding
- Layout proportions

### CORS Proxy

The default CORS proxy is `corsproxy.io`. If you have issues, alternatives include:
- `https://api.allorigins.win/raw?url=`
- Your own CORS proxy server
- Have your e-ink component fetch the calendar directly (bypasses CORS)

## Troubleshooting

**"Calendar not configured"**: Edit `calendar.js` and add your calendar URL

**"Failed to load calendar"**:
- Check that your calendar is set to public
- Verify the iCal URL is correct
- Try a different CORS proxy

**Events not showing**:
- Make sure you have future events in your calendar
- Check browser console for errors (F12)

**Layout issues**:
- Ensure viewport is set to exactly 800×480
- Test in full-screen mode
