from datetime import date, timedelta, datetime
import calendar
import logging
import re


import click
from dateutil.parser import parse
from jira import JIRA

from xycmd.config import CONFIG
from .models import Sprint, Issue, Worklog


def get_worklogs(project: str = None, worklog_author: str = None, days_ago: int = 0, since_date: str = None):
    since_date = since_date or None

    if since_date:
        if isinstance(since_date, datetime):
            since_date = since_date.date()
        elif isinstance(since_date, str):
            since_date = parse(since_date)
        else:
            # hopefully this is a date type by now, otherwise BOOM
            pass

    elif days_ago:
        since_date = datetime.now().date() - timedelta(days=days_ago)

    jira = JIRA(
        server=CONFIG.jira.server,
        basic_auth=(
            CONFIG.jira.username,
            CONFIG.jira.api_key
        ))

    query = []

    if project:
        query.append(f'project = {project}')

    if worklog_author:
        query.append(f'worklogAuthor = {worklog_author}')

    if since_date:
        query.append(f'worklogDate >= {str(since_date)}')

    # ordered to maximize chance of getting relevant issues first
    query = ' AND '.join(query) + ' ORDER BY updated DESC'

    tickets = jira.search_issues(
        jql_str=query,
        maxResults=0,
        fields=f'worklog,{CONFIG.jira.sprint_field_name}')

    days = {}
    worklogs = []
    sprints = {}

    for ticket in tickets:
        for worklog in ticket.fields.worklog.worklogs:
            ticket_sprints = []

            for s in getattr(ticket.fields, CONFIG.jira.sprint_field_name):
                sprint_id = re.search(r'id=(\d+)', s)
                if not sprint_id:
                    # well, nothing we can do about this
                    logging.debug(f'No sprint id found in {s}.')
                    continue

                sprint_id = sprint_id.group(1)

                if sprint_id not in sprints:
                    jira_sprint = jira.sprint(sprint_id)
                    sprints[sprint_id] = Sprint.from_jira(jira_sprint)

                ticket_sprints.append(sprints[sprint_id])

            # todo: make a from_jira function
            w = Worklog(
                issue=ticket.key,
                uid=worklog.id,
                time_spent=int(worklog.timeSpentSeconds),
                log_date=parse(worklog.started).date(),
                sprint=None)

            for s in ticket_sprints:
                if s.contains_worklog(w):
                    sprint = s
                    break

            w.sprint = sprint

            worklogs.append(w)

    # add sprint to worklogs based on time interval, rather than issue relationship
    for w in worklogs:
        if w.sprint:
            continue

        for s in sprints:
            if s.contains_worklog(w):
                w.sprint = s
                break

    sorted_sprints = {k: v for k, v in sorted(sprints.items(), key=lambda item: item[1].start_date or date(1970, 1, 1))}

    for s in sorted_sprints.values():
        if not s.end_date or not s.start_date:
            continue
        s.worklogs = {str(s.start_date + timedelta(days=k)): list() for k in range(0, (s.end_date - s.start_date).days + 1)}


    for w in worklogs:
        sprint = sorted_sprints[str(w.sprint.uid)]
        if str(w.log_date) not in sprint.worklogs:
            sprint.worklogs[str(w.log_date)] = list()

        sprint.worklogs[str(w.log_date)].append(w)

    for sprint in sorted_sprints.values():
        sprint_title = f'\nSprint "{sprint.name}" - {sprint.state}'
        click.secho(sprint_title, fg='green')

        fg = 'white'
        for day_str, worklogs in sprint.worklogs.items():

            total_h = 0
            total_d = 0
            wls_str = []

            for w in worklogs:
                total_h += w.time_spent_h
                wls_str.append(click.style(f'({w.issue} - {w.time_spent_h:2.2f}h)', fg='white'))

            wls_str = ', '.join(wls_str) or '-'

            total_d = round(total_h / CONFIG.jira.hours_per_day, 2)
            day = parse(day_str)

            if fg == 'white':
                fg = 'blue'
            else:
                fg = 'white'

            click.secho(f'    {day_str[2:]} - {calendar.day_name[day.weekday()][:3]} | {total_h:2.2f}h / {total_d:2.2f}d | {wls_str}', fg=fg)

    return jira, tickets, days
