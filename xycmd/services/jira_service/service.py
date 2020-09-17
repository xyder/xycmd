from datetime import date, timedelta, datetime
import calendar
import logging
import re


import click
from dateutil.parser import parse
from jira import JIRA
from tabulate import tabulate

from xycmd.config import CONFIG
from .models import Sprint, Issue, Worklog


def render_worklogs(sprints):
    table_header = ['Date', 'Logged (h / d)', 'Left (h)', 'Worklogs']

    for sprint in sprints.values():
        sprint_table = list()
        line_fg = 'white'

        for day_str, worklogs in sprint.worklogs.items():
            total_h = 0
            total_d = 0
            wls_str = []

            for w in worklogs:
                total_h += w.time_spent_h
                wls_str.append(click.style(f'({w.issue} - {w.time_spent_h:2.2f}h)', fg='white'))


            wls_str = ', '.join(wls_str) or '-'

            total_d = round(total_h / CONFIG.jira.hours_per_day, 2)

            week_day = calendar.day_name[parse(day_str).weekday()][:3]

            left_h = CONFIG.jira.hours_per_day - total_h
            if left_h < 0 or week_day in ['Sat', 'Sun']:
                left_h = 0

            line_fg = 'blue' if line_fg == 'white' else 'white'

            sprint_table.append([
                click.style(f'{week_day} {day_str}', fg=line_fg),
                click.style(f'{total_h:2.2f} / {total_d:2.2f}', fg=line_fg),
                '-' if left_h == 0 else click.style(f'{left_h:2.2f}', fg='red'),
                wls_str
                ])

        # render a sprint
        sprint_title = f'\nSprint "{sprint.name}" - {sprint.state}\n'
        click.secho(sprint_title, fg='green')

        click.echo(tabulate(sprint_table, headers=table_header, tablefmt='github'))


def get_tickets(jira, project=None, worklog_author=None, since_date=None):
    query = []

    if project:
        query.append(f'project = {project}')

    if worklog_author:
        query.append(f'worklogAuthor = "{worklog_author}"')

    if since_date:
        query.append(f'worklogDate >= {str(since_date)}')

    # ordered to maximize chance of getting relevant issues first
    query = ' AND '.join(query) + ' ORDER BY updated DESC'

    return jira.search_issues(
        jql_str=query,
        maxResults=0,
        fields=f'worklog,{CONFIG.jira.sprint_field_name}')



def gather_sprints_and_worklogs(jira, tickets, worklog_author):
    sprints = dict()
    worklogs = list()

    for ticket in tickets:

        ticket_sprints = []

        # gather the ticket sprints
        temp_sprints = getattr(ticket.fields, CONFIG.jira.sprint_field_name) or []
        for sprint in temp_sprints:
            sprint_id = str(sprint.id)

            sprints[sprint_id] = sprints.get(
                sprint_id, Sprint.from_jira(jira.sprint(sprint_id)))

            ticket_sprints.append(sprints[sprint_id])

        for worklog in ticket.fields.worklog.worklogs:
            if worklog_author and worklog.author.emailAddress != worklog_author:
                continue

            w = Worklog.from_jira(ticket.key, worklog)

            # todo: properly handle sprints without start and end dates or not started
            sprint = None
            for s in ticket_sprints:
                if s.contains_worklog(w):
                    sprint = s
                    break

            w.sprint = sprint

            worklogs.append(w)

    return sprints, worklogs


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

    tickets = get_tickets(jira, project, worklog_author, since_date)

    sprints, worklogs = gather_sprints_and_worklogs(jira, tickets, worklog_author)

    # add sprint to worklogs based on time interval, rather than issue relationship
    sprintless_worklogs = []
    for w in worklogs:
        if not w.sprint:
            for s in sprints.values():
                if s.contains_worklog(w):
                    w.sprint = s
                    break

        # still didn't find a sprint for this worklog
        if not w.sprint:
            sprintless_worklogs.append(w)
            continue

        sprint = sprints[str(w.sprint.uid)]
        log_date = str(w.log_date)

        sprint.worklogs[log_date] = sprint.worklogs.get(log_date, list())
        sprint.worklogs[log_date].append(w)

    sorted_sprints = {k: v for k, v in sorted(sprints.items(), key=lambda item: item[1].start_date or date(1970, 1, 1))}

    # add missing days to each sprint
    for s in sorted_sprints.values():
        if not s.end_date or not s.start_date:
            continue

        dates = {
            str(s.start_date + timedelta(days=k)): list()
            for k in range(0, (s.end_date - s.start_date).days + 1)}
        dates.update(s.worklogs)
        s.worklogs = dates

    return sorted_sprints, sprintless_worklogs


def fetch_and_render_worklogs(project: str = None, worklog_author: str = None, days_ago: int = 0, since_date: str = None):
    sorted_sprints, sprintless_worklogs = get_worklogs(
        project=project,
        worklog_author=worklog_author,
        days_ago=days_ago,
        since_date=since_date)

    render_worklogs(sorted_sprints)

    if sprintless_worklogs:
        click.echo()

        for w in sprintless_worklogs:
            click.secho(f'Warning: Found sprintless worklog for issue {w.issue} for {w.time_spent_h} h on {w.log_date}.', fg='red')
