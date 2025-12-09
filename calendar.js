// Configuration - Replace with your Google Calendar public iCal URL
const CALENDAR_CONFIG = {
    // Format: https://calendar.google.com/calendar/ical/YOUR_CALENDAR_ID/public/basic.ics
    calendarUrl: 'https://calendar.google.com/calendar/ical/family07866921202423959735%40group.calendar.google.com/private-1db2b054182d515d8be92313ea367a29/basic.ics',
    // Use CORS proxy to fetch the calendar (since browsers block direct iCal requests)
    corsProxy: 'https://corsproxy.io/?'
};

// Weather Configuration - Replace with your location coordinates
const WEATHER_CONFIG = {
    latitude: 43.4086299,
    longitude: -80.5045712,
    locationName: 'Kitchener, ON',
    units: 'celsius'
};

const MAX_EVENTS = 8;

// Initialize the calendar
document.addEventListener('DOMContentLoaded', () => {
    renderMonthCalendar();
    fetchAndDisplayEvents();
    fetchAndDisplayWeather();
});

// Render the current month calendar
function renderMonthCalendar() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();

    // Set month/year header
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('month-year').textContent = `${monthNames[month]} ${year}`;

    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    const calendarDays = document.getElementById('calendar-days');
    calendarDays.innerHTML = '';

    // Add previous month's days
    for (let i = firstDay - 1; i >= 0; i--) {
        const day = daysInPrevMonth - i;
        const dayDiv = createDayElement(day, 'other-month');
        calendarDays.appendChild(dayDiv);
    }

    // Add current month's days
    const today = now.getDate();
    for (let day = 1; day <= daysInMonth; day++) {
        const classes = [];
        if (day === today) {
            classes.push('today');
        }
        const dayDiv = createDayElement(day, ...classes);
        dayDiv.dataset.date = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        calendarDays.appendChild(dayDiv);
    }

    // Add next month's days to fill the grid
    const totalCells = calendarDays.children.length;
    const cellsNeeded = Math.ceil(totalCells / 7) * 7;
    for (let day = 1; day <= cellsNeeded - totalCells; day++) {
        const dayDiv = createDayElement(day, 'other-month');
        calendarDays.appendChild(dayDiv);
    }
}

function createDayElement(day, ...classes) {
    const div = document.createElement('div');
    div.className = 'calendar-day ' + classes.join(' ');
    div.textContent = day;
    return div;
}

// Fetch and display events from Google Calendar
async function fetchAndDisplayEvents() {
    const eventsList = document.getElementById('events-list');

    try {
        // Check if calendar URL is configured
        if (!CALENDAR_CONFIG.calendarUrl || CALENDAR_CONFIG.calendarUrl === 'YOUR_CALENDAR_URL_HERE') {
            eventsList.innerHTML = `
                <div class="error">
                    <p>Calendar not configured.</p>
                    <p style="margin-top: 10px; font-size: 12px;">Please edit calendar.js and set your Google Calendar public iCal URL.</p>
                </div>
            `;
            return;
        }

        // Fetch iCal data through CORS proxy
        const proxyUrl = CALENDAR_CONFIG.corsProxy + encodeURIComponent(CALENDAR_CONFIG.calendarUrl);
        const response = await fetch(proxyUrl);

        if (!response.ok) {
            throw new Error(`Failed to fetch calendar: ${response.status}`);
        }

        const icalData = await response.text();

        // Parse iCal data using ical.js
        const jcalData = ICAL.parse(icalData);
        const comp = new ICAL.Component(jcalData);
        const vevents = comp.getAllSubcomponents('vevent');

        // Convert to event objects
        const events = vevents.map(vevent => {
            const event = new ICAL.Event(vevent);
            return {
                summary: event.summary,
                location: event.location,
                startDate: event.startDate.toJSDate(),
                endDate: event.endDate.toJSDate(),
                description: event.description
            };
        });

        // Filter and sort events
        const now = new Date();
        const upcomingEvents = events
            .filter(event => event.startDate >= now)
            .sort((a, b) => a.startDate - b.startDate)
            .slice(0, MAX_EVENTS); 

        // Highlight calendar days with events
        highlightEventDays(events);

        // Display events
        displayEvents(upcomingEvents);

    } catch (error) {
        console.error('Error fetching calendar:', error);
        eventsList.innerHTML = `
            <div class="error">
                <p>Failed to load calendar.</p>
                <p style="margin-top: 10px; font-size: 12px;">${error.message}</p>
            </div>
        `;
    }
}

function highlightEventDays(events) {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();

    // Get all days in current month that have events
    const eventDates = new Set();
    events.forEach(event => {
        const eventDate = event.startDate;
        if (eventDate.getFullYear() === year && eventDate.getMonth() === month) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(eventDate.getDate()).padStart(2, '0')}`;
            eventDates.add(dateStr);
        }
    });

    // Add 'has-events' class to calendar days
    document.querySelectorAll('.calendar-day[data-date]').forEach(dayEl => {
        if (eventDates.has(dayEl.dataset.date)) {
            dayEl.classList.add('has-events');
        }
    });
}

function displayEvents(events) {
    const eventsList = document.getElementById('events-list');

    if (events.length === 0) {
        eventsList.innerHTML = '<div class="loading">No upcoming events</div>';
        return;
    }

    let html = '';
    let lastDate = '';

    events.forEach(event => {
        const startDate = event.startDate;
        const dateStr = formatDate(startDate);

        // Add date separator if this is a new day
        if (dateStr !== lastDate) {
            html += `<div class="event-date-separator">${dateStr}</div>`;
            lastDate = dateStr;
        }

        html += `
            <div class="event-item">
                <div class="event-time">${formatTime(startDate)}</div>
                <div class="event-title">${escapeHtml(event.summary)}</div>
                ${event.location ? `<div class="event-location">${escapeHtml(event.location)}</div>` : ''}
            </div>
        `;
    });

    eventsList.innerHTML = html;
}

function formatDate(date) {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    // Check if today or tomorrow
    if (isSameDay(date, today)) {
        return 'Today';
    } else if (isSameDay(date, tomorrow)) {
        return 'Tomorrow';
    }

    // Otherwise format as "Weekday, Month Day"
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    return `${days[date.getDay()]}, ${months[date.getMonth()]} ${date.getDate()}`;
}

function formatTime(date) {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';

    hours = hours % 12;
    hours = hours ? hours : 12; // 0 should be 12

    const minutesStr = minutes < 10 ? '0' + minutes : minutes;

    return `${hours}:${minutesStr} ${ampm}`;
}

function isSameDay(date1, date2) {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Fetch and display weather forecast
async function fetchAndDisplayWeather() {
    const weatherForecast = document.getElementById('weather-forecast');

    try {
        const tempUnit = WEATHER_CONFIG.units === 'celsius' ? 'celsius' : 'fahrenheit';
        const apiUrl = `https://api.open-meteo.com/v1/forecast?latitude=${WEATHER_CONFIG.latitude}&longitude=${WEATHER_CONFIG.longitude}&current=temperature_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min&temperature_unit=${tempUnit}&timezone=auto&forecast_days=5`;

        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error(`Failed to fetch weather: ${response.status}`);
        }

        const data = await response.json();
        displayWeather(data);

    } catch (error) {
        console.error('Error fetching weather:', error);
        weatherForecast.innerHTML = `
            <div class="error" style="padding: 10px; font-size: 12px;">
                Failed to load weather
            </div>
        `;
    }
}

function displayWeather(data) {
    const weatherForecast = document.getElementById('weather-forecast');
    const currentTemp = Math.round(data.current.temperature_2m);
    const currentCondition = getWeatherDescription(data.current.weather_code);
    const unit = WEATHER_CONFIG.units === 'celsius' ? '°C' : '°F';

    let html = `
        <div class="weather-current">
            <div class="weather-temp">${currentTemp}${unit}</div>
            <div>
                <div class="weather-condition">${currentCondition}</div>
                <div class="weather-location">${WEATHER_CONFIG.locationName}</div>
            </div>
        </div>
        <div class="weather-days">
    `;

    // Show next 4 days (skip today)
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    for (let i = 1; i <= 4; i++) {
        const date = new Date(data.daily.time[i]);
        const dayName = days[date.getDay()];
        const maxTemp = Math.round(data.daily.temperature_2m_max[i]);
        const minTemp = Math.round(data.daily.temperature_2m_min[i]);
        const weatherCode = data.daily.weather_code[i];
        const icon = getWeatherIcon(weatherCode);

        html += `
            <div class="weather-day">
                <div class="weather-day-name">${dayName}</div>
                <div class="weather-day-icon">${icon}</div>
                <div class="weather-day-temp">${maxTemp}° / ${minTemp}°</div>
            </div>
        `;
    }

    html += '</div>';
    weatherForecast.innerHTML = html;
}

function getWeatherDescription(code) {
    const descriptions = {
        0: 'Clear',
        1: 'Mostly Clear',
        2: 'Partly Cloudy',
        3: 'Cloudy',
        45: 'Foggy',
        48: 'Foggy',
        51: 'Light Drizzle',
        53: 'Drizzle',
        55: 'Heavy Drizzle',
        61: 'Light Rain',
        63: 'Rain',
        65: 'Heavy Rain',
        71: 'Light Snow',
        73: 'Snow',
        75: 'Heavy Snow',
        77: 'Snow Grains',
        80: 'Light Showers',
        81: 'Showers',
        82: 'Heavy Showers',
        85: 'Light Snow Showers',
        86: 'Snow Showers',
        95: 'Thunderstorm',
        96: 'Thunderstorm',
        99: 'Thunderstorm'
    };
    return descriptions[code] || 'Unknown';
}

function getWeatherIcon(code) {
    // Simple ASCII-friendly weather icons
    if (code === 0 || code === 1) return '☀';
    if (code === 2) return '⛅';
    if (code === 3) return '☁';
    if (code === 45 || code === 48) return '🌫';
    if (code >= 51 && code <= 55) return '🌦';
    if (code >= 61 && code <= 65) return '🌧';
    if (code >= 71 && code <= 77) return '❄';
    if (code >= 80 && code <= 82) return '🌧';
    if (code >= 85 && code <= 86) return '🌨';
    if (code >= 95 && code <= 99) return '⛈';
    return '?';
}
