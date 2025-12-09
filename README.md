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

### 4. For E-Ink Display

Once the web page is working, use your second component to:
1. Load the page in a headless browser or webview
2. Capture a screenshot at 800×480 resolution
3. Convert to the appropriate e-ink display format
4. Send to your e-ink display

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
