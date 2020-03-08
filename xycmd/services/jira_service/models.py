from datetime import date
from dataclasses import dataclass
from typing import Dict, List

from dateutil.parser import parse

from xycmd.config import CONFIG


class BaseModel:
    @classmethod
    def from_jira(cls, item, **kwargs):
        raise NotImplementedError


@dataclass
class Worklog(BaseModel):
    uid: str
    time_spent: int  # in seconds
    log_date: date
    sprint: 'Sprint'
    issue: 'Issue'

    @property
    def _time_spent_h_raw(self):
        return self.time_spent / 60 / 60

    @property
    def _time_spent_d_raw(self):
        return self._time_spent_h_raw / CONFIG.jira.hours_per_day

    @property
    def time_spent_h(self):
        return round(self._time_spent_h_raw, 2)

    @property
    def time_spent_d(self):
        return round(self._time_spent_d_raw, 2)


@dataclass
class Issue(BaseModel):
    uid: str
    key: str


@dataclass
class Sprint(BaseModel):
    uid: str
    start_date: date
    end_date: date
    name: str
    state: str

    issues: List[Issue]
    worklogs: Dict[str, Worklog]

    @classmethod
    def from_jira(cls, sprint):
        return cls(
            uid=sprint.id,
            start_date=parse(sprint.startDate).date() if sprint.startDate and sprint.startDate != 'None' else None,
            end_date=parse(sprint.endDate).date() if sprint.endDate and sprint.endDate != 'None' else None,
            name=sprint.name,
            state=sprint.state,
            issues=list(),  # todo: perhaps fetch issues too or fill them in somehow
            worklogs=dict()
        )

    def contains_worklog(self, worklog: Worklog):
        if not self.start_date or not self.end_date:
            return False

        return self.start_date <= worklog.log_date <= self.end_date