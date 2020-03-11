# xycmd

A CLI tool to make life easier in some specific ways

## Prerequisites

* Python 3.6+ (Tested with 3.7.4)
* Poetry: [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)
* Git

## Install

* Install prerequisites
* Clone the repo
* Run a variation of these:

```sh
cd path-to-repo

# install the app in a venv
poetry install

# copy configs and customize with your own values
cp example_config.toml config.toml
vim config.toml
```

## Usage

```sh
# show worklogs help
poetry run python xycmd jira worklogs --help

# show worklogs made by xyder@email.com in project PRJ starting 14 days ago and loop every 30 seconds.
poetry run python xycmd jira worklogs -p PRJ -a xyder@email.com -d 14 -l 30
```

## TODO

* [ ] break get_worklogs into pieces
* [ ] configurable colors
* [ ] installer
* [ ] worklogs: perhaps an option to limit to a sprint only

## Warranties

None that I know of. Use at your own risk.
Contributions accepted in the form of: issues, bug reports and PRs with issue and bug fixes, or "features".
Differences of opinion accepted in the form of repo forks (no metal forks pls).

## LICENSE

[MIT License](LICENSE)
