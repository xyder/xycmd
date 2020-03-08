
from time import sleep
from functools import partial

import click

from xycmd.config import CONFIG
from xycmd.services.jira_service import get_worklogs



def looper(cmd, sleep_seconds, *args, **kwargs):
    while True:
        click.clear()
        cmd(*args, **kwargs)
        sleep(sleep_seconds)


@click.group()
def cli():
    """ xycmd - a CLI toolset for specific purposes """
    pass


@cli.group()
def jira():
    """ JIRA commands """
    pass

@jira.command()
@click.option(
    '-l', '--loop', type=click.INT, default=0, help="Loop command execution every X seconds. Example: --loop 30")
@click.option(
    '-p', '--project', type=click.STRING, default='', help='Filter by JIRA project key.')
@click.option(
    '-a', '--worklog-author', type=click.STRING, default='', help='Filter by worklog author.')
@click.option(
    '-d', '--days', type=click.INT, default=0, help='Filter since X days ago.')
@click.option(
    '-s', '--since-date', type=click.DateTime(), default=None, help='Filter since date X.')
def worklogs(loop, project, worklog_author, days, since_date):
    """ Print a pretty table with worklogs. It is recommended to filter as much as possible, just in case. """

    cmd = partial(get_worklogs, project=project, worklog_author=worklog_author, days_ago=days, since_date=since_date)
    if loop:
        looper(cmd, loop)
    else:
        cmd()


if __name__ == "__main__":
    cli()
