from dataclasses import dataclass

import toml


@dataclass
class JiraConfig:
    server: str
    username: str
    api_key: str
    hours_per_day: int
    sprint_field_name: str


@dataclass
class AppConfig:
    jira: JiraConfig


def load_config(file_path):
    config_dict = toml.load(file_path)

    jira_config = config_dict['app'].pop('jira')
    return AppConfig(
        jira=JiraConfig(**jira_config),
        **config_dict['app']
    )


CONFIG = load_config(file_path='config.toml')