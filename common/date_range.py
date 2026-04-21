from dataclasses import dataclass
from datetime import date, timedelta
import calendar


@dataclass(frozen=True)
class DateRange:
    start_date: date
    end_date: date


def compute_date_range(
    refresh_mode: str,
    start_date: date | None = None,
    end_date: date | None = None,
    today: date | None = None,
) -> DateRange:
    """Compute execution date window from refresh mode.

    daily: yesterday (1 day)
    weekly: last 7 days including yesterday
    monthly: full previous month
    custom: explicit start_date/end_date
    """
    base = today or date.today()
    mode = refresh_mode.lower()

    if mode == "daily":
        day = base - timedelta(days=1)
        return DateRange(start_date=day, end_date=day)

    if mode == "weekly":
        end = base - timedelta(days=1)
        start = base - timedelta(days=7)
        return DateRange(start_date=start, end_date=end)

    if mode == "monthly":
        if base.month == 1:
            y, m = base.year - 1, 12
        else:
            y, m = base.year, base.month - 1
        last_day = calendar.monthrange(y, m)[1]
        return DateRange(start_date=date(y, m, 1), end_date=date(y, m, last_day))

    if mode == "custom":
        if not start_date or not end_date:
            raise ValueError("custom mode requires start_date and end_date")
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")
        return DateRange(start_date=start_date, end_date=end_date)

    raise ValueError(f"unsupported refresh_mode: {refresh_mode}")
