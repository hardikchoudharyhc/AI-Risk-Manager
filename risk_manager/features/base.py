from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any


@dataclass
class Features:
    """Base feature container. Subclass for each risk class."""
    transaction_id: str
    customer_id: str
    order_id: str
    timestamp: datetime
    
    def to_dict(self) -> dict[str, Any]:
        """Convert features to dictionary, handling Decimal/datetime."""
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
        return d


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division handling zero denominator."""
    return numerator / denominator if denominator != 0 else default


def days_between(dt1: datetime, dt2: datetime) -> int:
    """Days between two datetimes."""
    return max(0, (dt2 - dt1).days)


def velocity(events: list[datetime], time_window_hours: int) -> float:
    """Events per hour within time window."""
    if not events:
        return 0.0
    cutoff = events[-1] - timedelta(hours=time_window_hours)
    recent = [e for e in events if e >= cutoff]
    return len(recent) / time_window_hours if time_window_hours > 0 else 0.0
