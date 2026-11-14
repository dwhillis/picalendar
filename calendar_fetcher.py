"""
Calendar Fetcher - Fetch and parse Google Calendar iCal data
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
import requests
from icalendar import Calendar
from dateutil import rrule
from dateutil.tz import tzlocal, UTC

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    """Represents a calendar event"""
    summary: str
    start_date: datetime
    end_date: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    
    @property
    def is_all_day(self) -> bool:
        """Check if this is an all-day event"""
        return not hasattr(self.start_date, 'hour') or (
            self.start_date.hour == 0 and 
            self.start_date.minute == 0 and
            self.end_date.hour == 0 and
            self.end_date.minute == 0
        )


class CalendarFetcher:
    """Fetches and parses Google Calendar iCal data"""

    CACHE_PATH = None  # set in __init__ (allows tests to override)

    def __init__(self, calendar_url: str, timeout: int = 30):
        """Initialize calendar fetcher

        Args:
            calendar_url: Google Calendar iCal URL
            timeout: Request timeout in seconds
        """
        from pathlib import Path as _Path
        self.calendar_url = calendar_url
        self.timeout = timeout
        self._last_used_cache = False
        if self.CACHE_PATH is None:
            self.cache_path = _Path("/tmp/picalendar_cache_calendar.ics")
        else:
            self.cache_path = _Path(self.CACHE_PATH)

    def _save_cache(self, ical_data: str):
        try:
            self.cache_path.write_text(ical_data)
        except Exception as e:
            logger.warning(f"Failed to write calendar cache: {e}")

    def _load_cache(self) -> Optional[str]:
        try:
            if self.cache_path.exists():
                return self.cache_path.read_text()
        except Exception as e:
            logger.warning(f"Failed to read calendar cache: {e}")
        return None

    def fetch_events(self, max_events: int = 8, days_ahead: int = 90) -> List[CalendarEvent]:
        """Fetch upcoming events from Google Calendar

        Falls back to on-disk cache when the network fails, so the
        display keeps showing stale events with an offline indicator
        instead of going blank.

        Args:
            max_events: Maximum number of events to return
            days_ahead: How many days ahead to look for events

        Returns:
            List of CalendarEvent objects sorted by start date
        """
        try:
            logger.info(f"Fetching calendar from {self.calendar_url[:50]}...")

            response = requests.get(self.calendar_url, timeout=self.timeout)
            response.raise_for_status()

            ical_data = response.text
            self._save_cache(ical_data)
            self._last_used_cache = False
            return self._parse_ical(ical_data, max_events, days_ahead)

        except requests.RequestException as e:
            logger.error(f"Failed to fetch calendar: {e}")
            cached = self._load_cache()
            if cached:
                logger.info("Using cached calendar data")
                self._last_used_cache = True
                try:
                    return self._parse_ical(cached, max_events, days_ahead)
                except Exception as parse_e:
                    logger.error(f"Error parsing cached calendar: {parse_e}")
                    return []
            return []
        except Exception as e:
            logger.error(f"Error parsing calendar: {e}")
            return []
    
    def _parse_ical(self, ical_data: str, max_events: int, days_ahead: int) -> List[CalendarEvent]:
        """Parse iCal data and extract events
        
        Args:
            ical_data: Raw iCal string
            max_events: Maximum events to return
            days_ahead: Days to look ahead
            
        Returns:
            List of CalendarEvent objects
        """
        cal = Calendar.from_ical(ical_data)
        
        now = datetime.now(tzlocal())
        end_date = now + timedelta(days=days_ahead)
        range_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        events = []
        
        for component in cal.walk():
            if component.name != 'VEVENT':
                continue
            
            try:
                event_events = self._expand_event(component, range_start, end_date)
                events.extend(event_events)
            except Exception as e:
                summary = component.get('summary', 'Unknown')
                logger.warning(f"Error processing event '{summary}': {e}")
                continue
        
        # Filter to future events and sort
        upcoming = [e for e in events if e.start_date >= now]
        upcoming.sort(key=lambda x: x.start_date)
        
        return upcoming[:max_events]
    
    def _expand_event(self, component, range_start: datetime, range_end: datetime) -> List[CalendarEvent]:
        """Expand a single event, handling recurring events
        
        Args:
            component: iCal VEVENT component
            range_start: Start of date range
            range_end: End of date range
            
        Returns:
            List of CalendarEvent instances
        """
        summary = str(component.get('summary', 'No Title'))
        location = component.get('location')
        if location:
            location = str(location)
        description = component.get('description')
        if description:
            description = str(description)
        
        dtstart = component.get('dtstart')
        dtend = component.get('dtend')
        
        if not dtstart:
            return []
        
        start_dt = dtstart.dt
        
        # Handle date vs datetime
        if not isinstance(start_dt, datetime):
            start_dt = datetime.combine(start_dt, datetime.min.time())
            start_dt = start_dt.replace(tzinfo=tzlocal())
        elif start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=tzlocal())
        else:
            # Convert from original timezone (e.g., UTC) to local timezone
            start_dt = start_dt.astimezone(tzlocal())
        
        # Calculate duration
        if dtend:
            end_dt = dtend.dt
            if not isinstance(end_dt, datetime):
                end_dt = datetime.combine(end_dt, datetime.min.time())
                end_dt = end_dt.replace(tzinfo=tzlocal())
            elif end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=tzlocal())
            else:
                # Convert from original timezone to local timezone
                end_dt = end_dt.astimezone(tzlocal())
            duration = end_dt - start_dt
        else:
            duration = timedelta(hours=1)
        
        events = []
        
        # Check for recurrence
        rrule_prop = component.get('rrule')
        
        if rrule_prop:
            # Expand recurring event
            try:
                import re
                rrule_str = rrule_prop.to_ical().decode('utf-8')
                
                # Fix UNTIL timezone issue: if DTSTART is timezone-aware, UNTIL must be UTC
                if 'UNTIL=' in rrule_str and start_dt.tzinfo is not None:
                    # Handle both datetime and date-only UNTIL values
                    # Date-only: UNTIL=20250101
                    date_only_match = re.search(r'UNTIL=(\d{8})(?!T)', rrule_str)
                    if date_only_match:
                        # Convert date-only to datetime UTC
                        rrule_str = re.sub(r'UNTIL=(\d{8})(?!T)', r'UNTIL=\1T235959Z', rrule_str)
                    else:
                        # DateTime without Z: UNTIL=20250101T120000
                        until_match = re.search(r'UNTIL=(\d{8}T\d{6})(?!Z)', rrule_str)
                        if until_match:
                            rrule_str = re.sub(r'UNTIL=(\d{8}T\d{6})(?!Z)', r'UNTIL=\1Z', rrule_str)
                
                rule = rrule.rrulestr(
                    rrule_str,
                    dtstart=start_dt
                )
                
                # Get occurrences in range
                occurrences = list(rule.between(range_start, range_end, inc=True))[:100]
                
                for occ_start in occurrences:
                    if occ_start.tzinfo is None:
                        occ_start = occ_start.replace(tzinfo=tzlocal())
                    occ_end = occ_start + duration
                    
                    events.append(CalendarEvent(
                        summary=summary,
                        start_date=occ_start,
                        end_date=occ_end,
                        location=location,
                        description=description
                    ))
            except Exception as e:
                logger.warning(f"Error expanding recurring event '{summary}': {e}")
                # Fall back to single instance
                events.append(CalendarEvent(
                    summary=summary,
                    start_date=start_dt,
                    end_date=start_dt + duration,
                    location=location,
                    description=description
                ))
        else:
            # Single event
            events.append(CalendarEvent(
                summary=summary,
                start_date=start_dt,
                end_date=start_dt + duration,
                location=location,
                description=description
            ))
        
        return events
    
    def get_event_dates_for_month(self, year: int, month: int) -> set:
        """Get set of days in a month that have events (including past events)

        Falls back to cache on network failure.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Set of day numbers that have events
        """
        try:
            response = requests.get(self.calendar_url, timeout=self.timeout)
            response.raise_for_status()
            ical_data = response.text
            self._save_cache(ical_data)

            return self._event_dates_from_ical(ical_data, year, month)

        except Exception as e:
            logger.error(f"Error getting event dates: {e}")
            cached = self._load_cache()
            if cached:
                try:
                    return self._event_dates_from_ical(cached, year, month)
                except Exception:
                    pass
            return set()

    def _event_dates_from_ical(self, ical_data: str, year: int, month: int) -> set:
        cal = Calendar.from_ical(ical_data)

        # Date range for the target month
        month_start = datetime(year, month, 1, tzinfo=tzlocal())
        if month == 12:
            month_end = datetime(year + 1, 1, 1, tzinfo=tzlocal())
        else:
            month_end = datetime(year, month + 1, 1, tzinfo=tzlocal())

        event_days = set()

        for component in cal.walk():
            if component.name != 'VEVENT':
                continue

            try:
                events = self._expand_event(component, month_start, month_end)
                for event in events:
                    if event.start_date.year == year and event.start_date.month == month:
                        event_days.add(event.start_date.day)
            except Exception:
                continue

        return event_days
