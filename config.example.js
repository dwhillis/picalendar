// Google Calendar Configuration Example
// Copy this file to config.js and replace with your own settings

const CALENDAR_CONFIG = {
    // Format: https://calendar.google.com/calendar/ical/YOUR_CALENDAR_ID/public/basic.ics
    // To find your calendar ID, go to Google Calendar settings > Calendar > Integrate calendar > Copy the iCal link
    calendarUrl: 'YOUR_CALENDAR_URL_HERE',
    // Use CORS proxy to fetch the calendar (since browsers block direct iCal requests)
    corsProxy: 'https://corsproxy.io/?'
};

// Weather Configuration
// Replace with your location coordinates (latitude, longitude)
// You can find your coordinates at https://www.latlong.net/
const WEATHER_CONFIG = {
    latitude: 40.7128,      // Example: New York latitude
    longitude: -74.0060,    // Example: New York longitude
    locationName: 'New York, NY',
    units: 'fahrenheit'     // 'fahrenheit' or 'celsius'
};

const MAX_EVENTS = 8;
