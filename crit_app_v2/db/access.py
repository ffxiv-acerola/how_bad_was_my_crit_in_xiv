"""Database updates for analysis access tracking."""

import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from crit_app_v2.db.connection import get_connection


class PlayerAnalysisAccess(BaseModel):
    """Validated access event for a player-analysis record."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    analysis_id: str
    access_datetime: datetime.datetime

    def to_row(self) -> tuple[str, str]:
        """Map the access event to its database column order."""
        return self.analysis_id, self.access_datetime.isoformat()


def update_access_table(record: PlayerAnalysisAccess) -> None:
    """Record a validated access event for a player analysis."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
        insert into access (analysis_id, access_datetime)
        values (?, ?)
        """,
            record.to_row(),
        )
