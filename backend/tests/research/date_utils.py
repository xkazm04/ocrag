"""Date extraction and timeline utilities.

Extracts dates from text and orders events chronologically.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Tuple, Any
from enum import Enum


class DatePrecision(Enum):
    """Precision level of extracted date."""
    EXACT = "exact"      # Full date: 2022-02-24
    MONTH = "month"      # Month precision: 2022-02
    YEAR = "year"        # Year only: 2022
    RANGE = "range"      # Date range: 2014-2022
    APPROXIMATE = "approximate"  # Circa, around, early/late


@dataclass
class ExtractedDate:
    """A date extracted from text."""
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    precision: DatePrecision = DatePrecision.APPROXIMATE
    original_text: str = ""

    @property
    def sort_key(self) -> Tuple[int, int, int]:
        """Return tuple for sorting (year, month, day)."""
        if self.date_start:
            return (self.date_start.year, self.date_start.month, self.date_start.day)
        return (9999, 12, 31)  # Unknown dates sort last

    @property
    def display_text(self) -> str:
        """Human-readable date representation."""
        if not self.date_start:
            return self.original_text or "Unknown date"

        if self.precision == DatePrecision.EXACT:
            return self.date_start.strftime("%B %d, %Y")
        elif self.precision == DatePrecision.MONTH:
            return self.date_start.strftime("%B %Y")
        elif self.precision == DatePrecision.YEAR:
            return str(self.date_start.year)
        elif self.precision == DatePrecision.RANGE and self.date_end:
            return f"{self.date_start.year}-{self.date_end.year}"
        else:
            return self.original_text or self.date_start.strftime("%Y")


@dataclass
class TimelineEvent:
    """An event with extracted date for timeline ordering."""
    content: str
    summary: str
    extracted_date: ExtractedDate
    finding_type: str = "event"
    source_refs: List[str] = field(default_factory=list)

    @property
    def sort_key(self) -> Tuple[int, int, int]:
        return self.extracted_date.sort_key


class DateExtractor:
    """Extracts and normalizes dates from text."""

    # Month name mappings
    MONTHS = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }

    # Patterns for date extraction (ordered by specificity)
    PATTERNS = [
        # Full dates: February 24, 2022 or 24 February 2022
        (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', 'month_day_year'),
        (r'(\d{1,2})\s+(\w+),?\s+(\d{4})', 'day_month_year'),
        # ISO format: 2022-02-24
        (r'(\d{4})-(\d{2})-(\d{2})', 'iso'),
        # Month Year: February 2022
        (r'(\w+)\s+(\d{4})', 'month_year'),
        # Year ranges: 2014-2022
        (r'(\d{4})\s*[-–—to]+\s*(\d{4})', 'year_range'),
        # Standalone year
        (r'\b((?:19|20)\d{2})\b', 'year_only'),
        # Relative: early/mid/late 2022
        (r'(early|mid|late)\s+(\d{4})', 'relative_year'),
        # Seasons: spring 2022
        (r'(spring|summer|fall|autumn|winter)\s+(\d{4})', 'season_year'),
    ]

    def extract(self, text: str) -> ExtractedDate:
        """Extract the most specific date from text."""
        text_lower = text.lower()

        # Try patterns in order of specificity
        for pattern, pattern_type in self.PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                result = self._parse_match(match, pattern_type, text)
                if result.date_start:
                    return result

        # No date found
        return ExtractedDate(
            precision=DatePrecision.APPROXIMATE,
            original_text="",
        )

    def extract_all(self, text: str) -> List[ExtractedDate]:
        """Extract all dates from text."""
        dates = []
        text_lower = text.lower()

        for pattern, pattern_type in self.PATTERNS:
            for match in re.finditer(pattern, text_lower):
                result = self._parse_match(match, pattern_type, text)
                if result.date_start:
                    dates.append(result)

        # Remove duplicates and sort
        seen = set()
        unique_dates = []
        for d in dates:
            key = (d.date_start, d.date_end, d.precision)
            if key not in seen:
                seen.add(key)
                unique_dates.append(d)

        return sorted(unique_dates, key=lambda x: x.sort_key)

    def _parse_match(
        self, match: re.Match, pattern_type: str, original_text: str
    ) -> ExtractedDate:
        """Parse a regex match into an ExtractedDate."""
        try:
            if pattern_type == 'month_day_year':
                month_str, day, year = match.groups()
                month = self.MONTHS.get(month_str.lower())
                if month:
                    return ExtractedDate(
                        date_start=date(int(year), month, int(day)),
                        precision=DatePrecision.EXACT,
                        original_text=match.group(0),
                    )

            elif pattern_type == 'day_month_year':
                day, month_str, year = match.groups()
                month = self.MONTHS.get(month_str.lower())
                if month:
                    return ExtractedDate(
                        date_start=date(int(year), month, int(day)),
                        precision=DatePrecision.EXACT,
                        original_text=match.group(0),
                    )

            elif pattern_type == 'iso':
                year, month, day = match.groups()
                return ExtractedDate(
                    date_start=date(int(year), int(month), int(day)),
                    precision=DatePrecision.EXACT,
                    original_text=match.group(0),
                )

            elif pattern_type == 'month_year':
                month_str, year = match.groups()
                month = self.MONTHS.get(month_str.lower())
                if month:
                    return ExtractedDate(
                        date_start=date(int(year), month, 1),
                        precision=DatePrecision.MONTH,
                        original_text=match.group(0),
                    )

            elif pattern_type == 'year_range':
                start_year, end_year = match.groups()
                return ExtractedDate(
                    date_start=date(int(start_year), 1, 1),
                    date_end=date(int(end_year), 12, 31),
                    precision=DatePrecision.RANGE,
                    original_text=match.group(0),
                )

            elif pattern_type == 'year_only':
                year = match.group(1)
                return ExtractedDate(
                    date_start=date(int(year), 6, 15),  # Mid-year for sorting
                    precision=DatePrecision.YEAR,
                    original_text=year,
                )

            elif pattern_type == 'relative_year':
                period, year = match.groups()
                month = {'early': 2, 'mid': 6, 'late': 10}.get(period, 6)
                return ExtractedDate(
                    date_start=date(int(year), month, 15),
                    precision=DatePrecision.APPROXIMATE,
                    original_text=match.group(0),
                )

            elif pattern_type == 'season_year':
                season, year = match.groups()
                month = {
                    'spring': 4, 'summer': 7,
                    'fall': 10, 'autumn': 10, 'winter': 1
                }.get(season, 6)
                return ExtractedDate(
                    date_start=date(int(year), month, 15),
                    precision=DatePrecision.APPROXIMATE,
                    original_text=match.group(0),
                )

        except (ValueError, TypeError):
            pass

        return ExtractedDate()


class TimelineBuilder:
    """Builds ordered timelines from events."""

    def __init__(self):
        self.date_extractor = DateExtractor()

    def build_timeline(
        self,
        events: List[Any],
        content_field: str = "content",
        summary_field: str = "summary",
    ) -> List[TimelineEvent]:
        """Build an ordered timeline from a list of events/findings."""
        timeline_events = []

        for event in events:
            content = getattr(event, content_field, "") or ""
            summary = getattr(event, summary_field, "") or content[:100]
            finding_type = getattr(event, "finding_type", "event")

            # Extract date from content
            extracted_date = self.date_extractor.extract(content)

            # Also try summary if content didn't have a date
            if not extracted_date.date_start and summary:
                extracted_date = self.date_extractor.extract(summary)

            timeline_events.append(TimelineEvent(
                content=content,
                summary=summary,
                extracted_date=extracted_date,
                finding_type=finding_type,
            ))

        # Sort by date
        return self._sort_timeline(timeline_events)

    def _sort_timeline(
        self, events: List[TimelineEvent]
    ) -> List[TimelineEvent]:
        """Sort events chronologically."""
        # Separate dated and undated events
        dated = [e for e in events if e.extracted_date.date_start]
        undated = [e for e in events if not e.extracted_date.date_start]

        # Sort dated events
        dated.sort(key=lambda e: e.sort_key)

        # Return dated first, then undated
        return dated + undated

    def format_timeline(
        self,
        events: List[TimelineEvent],
        include_undated: bool = False,
    ) -> str:
        """Format timeline as readable text."""
        lines = []

        for event in events:
            if not include_undated and not event.extracted_date.date_start:
                continue

            date_str = event.extracted_date.display_text
            summary = event.summary[:80] if event.summary else event.content[:80]

            lines.append(f"  {date_str}: {summary}")

        return "\n".join(lines)


# Module-level instances for convenience
_date_extractor = DateExtractor()
_timeline_builder = TimelineBuilder()


def extract_date(text: str) -> ExtractedDate:
    """Extract date from text."""
    return _date_extractor.extract(text)


def extract_all_dates(text: str) -> List[ExtractedDate]:
    """Extract all dates from text."""
    return _date_extractor.extract_all(text)


def build_timeline(events: List[Any]) -> List[TimelineEvent]:
    """Build ordered timeline from events."""
    return _timeline_builder.build_timeline(events)


def format_timeline(events: List[TimelineEvent]) -> str:
    """Format timeline as text."""
    return _timeline_builder.format_timeline(events)
