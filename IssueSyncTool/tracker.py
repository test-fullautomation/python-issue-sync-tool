from .rtc_client import RTCClient
from github import Github, Auth
from jira import JIRA, Issue
from gitlab import Gitlab
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union, Optional, Callable
import re

class Status:
   """
Class representing the status of issues in different tracker systems.
   """
   STATUS_MAPPING = {
      "github": {
         "open": "Open",
         "closed": "Closed"
      },
      "gitlab": {
         "opened": "Open",
         "closed": "Closed"
      },
      "jira": {
         "Open": "Open",
         "In Progress": "In Progress",
         "Resolved": "Closed",
         "Closed": "Closed"
      },
      "rtc": {
         "New": "Open",
         "In Development": "In Progress",
         "Done": "Closed"
      }
   }
   
   open = "Open"
   inProgress = "In Progress"
   closed = "Closed"

   @staticmethod
   def normalize_issue_status(tracker_type: str, native_status: str) -> str:
      """
Normalize the issue status to a standard format.

**Arguments:**

* ``tracker_type``

  / *Condition*: required / *Type*: str /

  The type of tracker (e.g., github, gitlab, jira, rtc).

* ``native_status``

  / *Condition*: required / *Type*: str /

  The native status of the issue.

**Returns:**

* ``normalized_status``

  / *Type*: str /

  The normalized status of the issue.
      """
      if tracker_type not in Status.STATUS_MAPPING.keys():
         raise ValueError(f"Unsupported tracker type {tracker_type}")
      
      if native_status not in Status.STATUS_MAPPING[tracker_type].keys():
         raise ValueError(f"Unsupported status {native_status} for {tracker_type.title()} issue")
      
      return Status.STATUS_MAPPING[tracker_type][native_status]
   
   @staticmethod
   def get_native_status(tracker_type: str, normalized_status: str) -> str:
      """
Get the native status from the normalized status.

**Arguments:**

* ``tracker_type``

  / *Condition*: required / *Type*: str /

  The type of tracker (e.g., github, gitlab, jira, rtc).

* ``normalized_status``

  / *Condition*: required / *Type*: str /

  The normalized status of the issue.

**Returns:**

* ``native_status``

  / *Type*: str /

  The native status of the issue.
      """
      if tracker_type not in Status.STATUS_MAPPING.keys():
         raise Exception(f"Unsupported tracker type {tracker_type}")
      
      if normalized_status not in Status.STATUS_MAPPING[tracker_type].values():
         raise Exception(f"Unsupported status {normalized_status}")
      
      for key, val in Status.STATUS_MAPPING[tracker_type].items():
         if val == normalized_status: 
            return key 

class Ticket:
   """
Normalized Ticket with required information for syncing between trackers.
   """

   def __init__(self,
                tracker: str,
                original_id: Optional[str] = None,
                title: Optional[str] = None,
                description: Optional[str] = None,
                assignee: Union[str, list] = None,
                url: Optional[str] = None,
                status: Optional[str] = None,
                component: Optional[str] = None,
                version: Optional[str] = None,
                story_point: Optional[int] = None,
                createdDate: Optional[str] = None,
                updatedDate: Optional[str] = None,
                labels: Optional[list] = None,
                destination_id: Optional[str] = None,
                issue_client: Callable = None):
      """
Initialize a new Ticket.

**Arguments:**

* ``tracker``

  / *Condition*: required / *Type*: str /

  The type of tracker (e.g., github, gitlab, jira, rtc).

* ``original_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The original ID of the ticket.

* ``title``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The title of the ticket.

* ``description``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The description of the ticket.

* ``assignee``

  / *Condition*: optional / *Type*: Union[str, list] / *Default*: None /

  The assignee of the ticket.

* ``url``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The URL of the ticket.

* ``status``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The status of the ticket.

* ``component``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The component of the ticket.

* ``version``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The version of the ticket.

* ``story_point``

  / *Condition*: optional / *Type*: int / *Default*: None /

  The story points of the ticket.

* ``createdDate``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The creation date of the ticket.

* ``updatedDate``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The last updated date of the ticket.

* ``labels``

  / *Condition*: optional / *Type*: list / *Default*: [] /

  The labels associated with the ticket.

* ``destination_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The destination ID of the ticket.

* ``issue_client``

  / *Condition*: optional / *Type*: Callable / *Default*: None /

  The issue client for interacting with the tracker.
      """
      self.tracker = tracker
      self.id = original_id
      self.title = title
      self.description = description
      self.assignee = assignee
      self.url = url
      self.status = status
      self.createdDate = createdDate
      self.updatedDate = updatedDate
      self.component = component
      self.version = version
      self.labels = labels if labels is not None else []
      self.story_point = story_point
      self.destination_id = destination_id
      self.issue_client = issue_client

   def __repr__(self):
      """
Return a string representation of the Ticket object.

**Returns:**

* ``representation``

  / *Type*: str /

  A string representation of the Ticket object.
      """
      return (f"Ticket ({self.tracker.capitalize()}: ID={self.id}, title=\"{self.title}\")")

   def update(self, **kwargs):
      """
Update issue on tracker with following supported attributes:
 - title
 - assignee
 - labels

**Arguments:**

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  A dictionary of attributes to update the ticket with.
      """
      if self.issue_client:
         if self.tracker == "gitlab":
            self._update_gitlab_issue(**kwargs)
         elif self.tracker == "github":
            self._update_github_issue(**kwargs)
         elif self.tracker == "jira":
            self._update_jira_issue(**kwargs)
         elif self.tracker == 'rtc':
            self._update_rtc_issue(**kwargs)
      else:
         raise NotImplementedError(f"No implementation to update {self.tracker.title()} issue.")

   def _update_gitlab_issue(self, **kwargs):
      for attr, val in kwargs.items():
         if hasattr(self.issue_client, attr):
            setattr(self.issue_client, attr, val)
         else:
            raise AttributeError(f"'{type(self.issue_client).__name__}' object has no attribute '{attr}'")
      self.issue_client.save()

   def _update_github_issue(self, **kwargs):
      self.issue_client.edit(**kwargs)

   def _update_jira_issue(self, **kwargs):
      if 'assignee' in kwargs:
         assignee_val = {"name": kwargs['assignee']}
         kwargs['assignee'] = assignee_val
      if 'title' in kwargs:
         title_val = kwargs['title']
         kwargs['summary'] = title_val
         del kwargs['title']
      if 'labels' in kwargs:
         kwargs['fields'] = {
            'labels': list()
         }
         # JIRA label does not allow space
         for label in kwargs['labels']:
            kwargs['fields']['labels'].append(label.replace(" ", "_"))
         del kwargs['labels']
      self.issue_client.update(**kwargs)

   def _update_rtc_issue(self, **kwargs):
      self.issue_client.update_workitem(self.id, **kwargs)

   def is_synced_issue(self):
      """
Verify whether the ticket is already synced or not.

It bases on the title of issue, it should contain destination ID information.
E.g `[ 1234 ] Title of already synced ticket`

**Returns:**

* ``is_synced``

  / *Type*: bool /

  Indicates if the ticket is already synced.
      """
      match = re.search(r"^\[\s*(\d+)\s*\]", self.title)
      if match:
         self.destination_id = match.group(1)
         return True
      return False
   
class TrackerService(ABC):
   """
Abstraction class of Tracker Service.
   """
   # Number of hours equivalent to one story point.
   HOUR_PER_STORYPOINT = 8

   # Default color for sprint labels.
   SPRINT_LABEL_COLOR = "#007bff"  # calm blue

   def __init__(self):
      """
Initialize the TrackerService instance.
      """
      self.tracker_client = None

   @abstractmethod
   def connect(self, *args, **kwargs):
      """
Method to connect to the tracker.
      """
      pass

   @abstractmethod
   def get_ticket(self, id: Union[str, int]) -> Ticket:
      """
Method to get a single ticket by ID from the tracker.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: Union[str, int] /

  The ID of the ticket.

**Returns:**

* ``ticket``

  / *Type*: Ticket /

  The ticket object.
      """
      pass

   @abstractmethod
   def get_tickets(self, **kwargs) -> list[Ticket]:
      """
Method to get all tickets which satisfy the given condition/query.

**Arguments:**

* ``kwargs``

  / *Condition*: optional / *Type*: dict /

  Additional keyword arguments for filtering tickets.

**Returns:**

* ``tickets``

  / *Type*: list[Ticket] /

  A list of tickets that satisfy the given conditions.
      """
      pass

   @abstractmethod
   def create_ticket(self, ticket: Ticket) -> str:
      """
Method to create a new ticket on the tracker system.

**Arguments:**

* ``ticket``

  / *Condition*: required / *Type*: Ticket /

  The ticket object to be created.

**Returns:**

* ``ticket_id``

  / *Type*: str /

  The ID of the created ticket.
      """
      pass

   def exclude_issue_by_condition(self, issue: Issue, exclude_condition=None) -> bool:
      """
Process to verify whether the given issue satisfies the exclude conditions.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: Issue /

  The issue object to be checked.

* ``exclude_condition``

  / *Condition*: optional / *Type*: dict / *Default*: None /

  A dictionary of conditions to exclude the issue.

**Returns:**

* ``is_excluded``

  / *Type*: bool /

  Indicates if the issue is excluded based on the given conditions.
      """
      if exclude_condition:
         for key, value in exclude_condition.items():
            if key in ["assignee", "labels"]:
               if not getattr(issue, key):
                  if value == "empty": return False
               else:
                  if value in getattr(issue, key): return False
            else:
               if getattr(issue, key) == value: return False
      return True

   def get_story_point_from_labels(self, labels: list) -> int:
      """
Process to get story points from issue labels.
Example of story point labels: `1 point`, `2 points`, ...

**Arguments:**

* ``labels``

  / *Condition*: required / *Type*: list /

  A list of labels associated with the issue.

**Returns:**

* ``story_points``

  / *Type*: int /

  The story points extracted from the labels.
      """
      for label in labels:
         story_point_label = re.match(r'(\d+)\s*point(s)?', label)
         if story_point_label:
            return int(story_point_label[1])

      return 0

   @classmethod
   def time_estimate_to_story_point(cls, seconds: int) -> int:
      """
Convert given estimated time (in seconds) to story points.

**Arguments:**

* ``seconds``

  / *Condition*: required / *Type*: int /

  The estimated time in seconds.

**Returns:**

* ``story_points``

  / *Type*: int /

  The equivalent story points for the given estimated time.
      """
      if not isinstance(seconds, int) or seconds < 0:
         raise ValueError("seconds must be a non-negative integer")
      return int(seconds / 3600 / cls.HOUR_PER_STORYPOINT)
   
class JiraTracker(TrackerService):
   """
Tracker client to integrate with issues on Jira.
   """
   TYPE = "jira"

   def __init__(self):
      """
Initialize the JiraTracker instance.
      """
      super().__init__()
      self.project = None
      self.hostname = None

   def __normalize_issue(self, issues: list) -> list[Ticket]:
      """
Normalize a list of issues to Ticket objects.

**Arguments:**

* ``issues``

  / *Condition*: required / *Type*: list /

  A list of issues to normalize.

**Returns:**

* ``tickets``

  / *Type*: list[Ticket] /

  A list of Ticket objects created from the issue data.
      """
      return [Ticket(self.TYPE,
                     issue.key,
                     issue.raw['fields']['summary'],
                     issue.raw['fields']['description'],
                     issue.raw['fields']['assignee']['name'] if issue.raw['fields']['assignee'] else None,
                     f"{self.hostname}/browse/{issue.key}",
                     Status.normalize_issue_status(self.TYPE, issue.raw['fields']['status']['name']),
                     self.__get_component(issue),
                     story_point=self.get_story_point(issue),
                     labels=issue.raw['fields']['labels'],
                     issue_client=issue
                     ) for issue in issues]

   def __get_component(self, issue):
      if len(issue.raw['fields']['components']) > 0:
         return issue.raw['fields']['components'][0]['name']
      return None

   def connect(self, project: str, token: str, hostname: str):
      """
Connect to the Jira tracker.

**Arguments:**

* ``project``

  / *Condition*: required / *Type*: str /

  The project name.

* ``token``

  / *Condition*: required / *Type*: str /

  The access token.

* ``hostname``

  / *Condition*: required / *Type*: str /

  The hostname of the Jira server.
      """
      self.project = project
      self.hostname = hostname
      self.tracker_client = JIRA(hostname, token_auth=token)
   
   def get_ticket(self, id: str) -> Ticket:
      """
Get a ticket by its ID.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: str /

  The ID of the ticket.

**Returns:**

* ``ticket``

  / *Type*: Ticket /

  The ticket object.
      """
      issue = self.tracker_client.issue(id)
      return self.__normalize_issue([issue])[0]

   def get_tickets(self, **kwargs) -> list[Ticket]:
      """
Get tickets from the Jira tracker.

**Arguments:**

* ``kwargs``

  / *Condition*: optional / *Type*: dict /

  Additional keyword arguments for filtering tickets.

**Returns:**

* ``tickets``

  / *Type*: list[Ticket] /

  A list of tickets that satisfy the given conditions.
      """
      list_issues = list()
      jql = list()
      jql.append(f'project={self.project}')
      exclude_condition = None
      if 'exclude' in kwargs:
         exclude_condition = kwargs['exclude']
         del kwargs['exclude']
         for key, val in exclude_condition.items():
            if val:
               if isinstance(val, list):
                  jql.append(f"{key} not in ({','.join(val)})")
               elif isinstance(val, str):
                  jql.append(f"{key} != {val}")

      for key, val in kwargs.items():
         if val:
            if isinstance(val, list):
               jql.append(f"{key} in ({','.join(val)})")
            elif isinstance(val, str):
               jql.append(f"{key} = {val}")

      list_issues = self.tracker_client.search_issues(" AND ".join(jql))
      issues = self.__normalize_issue(list_issues)
      return issues

   def create_ticket(self, project: str = None, **kwargs) -> str:
      """
Create a new ticket in the Jira tracker.

**Arguments:**

* ``project``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project name.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for creating the ticket.

**Returns:**

* ``ticket_id``

  / *Type*: str /

  The ID of the created ticket.
      """
      if 'issuetype' not in kwargs:
         kwargs['issuetype'] = {"name": "Story"}
      if 'assignee' in kwargs:
         assignee_val = {"name" : kwargs['assignee']}
         kwargs['assignee'] = assignee_val

      if not project:
         project = self.project
      issue = self.tracker_client.create_issue(project=project, **kwargs)
      return issue.key

   def update_ticket(self, id: str, **kwargs):
      """
Update an existing ticket in the Jira tracker.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: str /

  The ID of the ticket to update.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for updating the ticket.
      """
      edit_issue = self.tracker_client.issue(id)
      edit_issue.update(**kwargs)

   def get_story_point(self, issue) -> int:
      """
Get the story points of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: Issue /

  The issue object.

**Returns:**

* ``story_points``

  / *Type*: int /

  The story points of the issue.
      """
      # customfield_10224 from API response contains Estimate story point attribute
      if 'customfield_10224' in issue.raw['fields'] and issue.raw['fields']['customfield_10224']:
         return int(issue.raw['fields']['customfield_10224'])
   
      # convert estimation time to story point
      # if 'timetracking' in issue.raw['fields'] and issue.raw['fields']['timetracking'] and 'remainingEstimateSeconds' in issue.raw['fields']['timetracking']:
      #    return self.time_estimate_to_story_point(issue.raw['fields']['timetracking']['remainingEstimateSeconds'])
      return 0

   def create_label(self, label_name: str, color: str = None, repository: str = None):
      """
Jira does not require to create label before, label can be add directly in ticket.

**Arguments:**

* ``label_name``

  / *Condition*: required / *Type*: str /

  The name of the label.

* ``color``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The color of the label.

* ``repository``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The repository name.
      """
      pass

class GithubTracker(TrackerService):
   """
Tracker client to integrate with issues on GitHub.
   """
   TYPE = "github"

   def __init__(self):
      """
Initialize the GithubTracker instance.
      """
      super().__init__()
      self.repositories = list()
      self.project = None

   def __normalize_issue(self, issue: str, repo: str) -> Ticket:
      """
Normalize an issue to a Ticket object.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: str /

  The issue data.

* ``repo``

  / *Condition*: required / *Type*: str /

  The repository name.

**Returns:**

* ``ticket``

  / *Type*: Ticket /

  A Ticket object created from the issue data.
      """
      return Ticket(self.TYPE,
                    issue.number,
                    issue.title,
                    issue.body,
                    [assignee.login for assignee in issue.assignees],
                    issue.html_url,
                    Status.normalize_issue_status(self.TYPE, issue.state),
                    repo,
                    labels=[label.name for label in issue.labels],
                    story_point=self.get_story_point_from_labels([label.name for label in issue.labels]),
                    issue_client=issue)
   
   def __get_repository_client(self, repository: str = None):
      """
Get the repository client for the specified repository.

**Arguments:**

* ``repository``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The repository name.

**Returns:**

* ``repository_client``

  / *Type*: Repository /

  The repository client.
      """
      if repository:
         return self.tracker_client.get_repo(f"{self.project}/{repository}")
      elif self.repositories:
         if len(self.repositories) == 1:
            return self.tracker_client.get_repo(f"{self.project}/{self.repositories[0]}")
         else:
            raise Exception(f"More than one GitHub repository is configured, please specify the working repository")
      else:
         raise Exception(f"Missing GitHub repository information")
      
   def connect(self, project: str, repository: Union[list, str], token: str, hostname: str = "api.github.com"):
      """
Connect to the GitHub tracker.

**Arguments:**

* ``project``

  / *Condition*: required / *Type*: str /

  The project name.

* ``repository``

  / *Condition*: required / *Type*: Union[list, str] /

  The repository name(s).

* ``token``

  / *Condition*: required / *Type*: str /

  The access token.

* ``hostname``

  / *Condition*: optional / *Type*: str / *Default*: "api.github.com" /

  The hostname of the GitHub server.
      """
      self.project = project
      if isinstance(repository, list):
         self.repositories = repository
      elif isinstance(repository, str):
         self.repositories = [repository]
      else:
         raise Exception("'repository' parameter should be list of repositories or string of single repo")
      auth = Auth.Token(token)
      self.tracker_client = Github(auth=auth, base_url=f"https://{hostname}")
   
   def get_tickets(self, **kwargs) -> list[Ticket]:
      """
Get tickets from the GitHub tracker.

**Arguments:**

* ``kwargs``

  / *Condition*: optional / *Type*: dict /

  Additional keyword arguments for filtering tickets.

**Returns:**

* ``tickets``

  / *Type*: list[Ticket] /

  A list of tickets that satisfy the given conditions.
      """
      list_issues = list()
      exclude_condition = None
      if 'exclude' in kwargs:
         exclude_condition = kwargs['exclude']
         del kwargs['exclude']
      for repo in self.repositories:
         con_repo = self.tracker_client.get_repo(f"{self.project}/{repo}")
         issues = con_repo.get_issues(**kwargs)
         for issue in issues:
            if not issue.pull_request:
               issue = self.__normalize_issue(issue, repo)
               if self.exclude_issue_by_condition(issue, exclude_condition):
                  list_issues.append(issue)

      return list_issues
   
   def get_ticket(self, id: int, repository: str = None) -> Ticket:
      """
Get a ticket by its ID.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: int /

  The ID of the ticket.

* ``repository``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The repository name.

**Returns:**

* ``ticket``

  / *Type*: Ticket /

  The ticket object.
      """
      gh_repo = self.__get_repository_client(repository)
      issue = gh_repo.get_issue(id)
      return self.__normalize_issue(issue, gh_repo.name)

   def create_ticket(self, repository: str = None, **kwargs) -> str:
      """
Create a new ticket in the GitHub tracker.

**Arguments:**

* ``repository``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The repository name.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for creating the ticket.

**Returns:**

* ``ticket_id``

  / *Type*: str /

  The ID of the created ticket.
      """
      gh_repo = self.__get_repository_client(repository)
      issue = gh_repo.create_issue(**kwargs)
      return issue.number

   def update_ticket(self, id: int, repository: str = None, **kwargs):
      """
Update an existing ticket in the GitHub tracker.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: int /

  The ID of the ticket to update.

* ``repository``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The repository name.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for updating the ticket.
      """
      gh_repo = self.__get_repository_client(repository)
      edit_issue = gh_repo.get_issue(id)
      edit_issue.edit(**kwargs)

   def create_label(self, label_name: str, color: str = None, repository: str = None):
      """
Create a new label in the GitHub tracker.

**Arguments:**

* ``label_name``

  / *Condition*: required / *Type*: str /

  The name of the label.

* ``color``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The color of the label.

* ``repository``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The repository name.
      """
      gh_repo = self.__get_repository_client(repository)
      list_existing_labels = gh_repo.get_labels()
      for item in list_existing_labels:
         if item.name == label_name:
            return

      label_pros = {
         'name': label_name,
         'color': color if color else self.SPRINT_LABEL_COLOR
      }
      
      label_pros['color'] = label_pros['color'].replace('#', '')
      gh_repo.create_label(**label_pros)

class GitlabTracker(TrackerService):
   """
Tracker client to integrate with issues on Gitlab.

Except, `get_tickets` which allow to get issues from gitlab, group and project level,
other method requires `project` information to interact properly with inside issues.
   """
   TYPE = "gitlab"

   def __init__(self):
      """
Initialize the GitlabTracker instance.
      """
      super().__init__()

   def __normalize_issue(self, issue, project):
      """
Normalize an issue to a Ticket object.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``ticket``

  / *Type*: Ticket /

  A Ticket object created from the issue data.
      """
      return Ticket(
         self.TYPE,
         self.__get_issue_id(issue),
         self.__get_issue_title(issue),
         self.__get_issue_description(issue),
         self.__get_issue_assignee(issue),
         self.__get_issue_url(issue),
         self.__get_issue_status(issue),
         project,
         labels=self.__get_issue_labels(issue),
         story_point=self.get_story_point(issue),
         issue_client=issue
      )

   def __get_issue_id(self, issue):
      """
Get the identifier of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``identifier``

  / *Type*: str /

  The identifier of the issue.
      """
      return issue.iid

   def __get_issue_title(self, issue):
      """
Get the title of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``title``

  / *Type*: str /

  The title of the issue.
      """
      return issue.title

   def __get_issue_description(self, issue):
      """
Get the description of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``description``

  / *Type*: str /

  The description of the issue.
      """
      return issue.description

   def __get_issue_assignee(self, issue):
      """
Get the assignee of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``assignee``

  / *Type*: str /

  The assignee of the issue.
      """
      return issue.assignee['username']

   def __get_issue_url(self, issue):
      """
Get the URL of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``url``

  / *Type*: str /

  The URL of the issue.
      """
      return issue.web_url

   def __get_issue_status(self, issue):
      """
Get the status of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``status``

  / *Type*: str /

  The status of the issue.
      """
      return Status.normalize_issue_status(self.TYPE, issue.state)

   def __get_issue_labels(self, issue):
      """
Get the labels of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``labels``

  / *Type*: list /

  The labels of the issue.
      """
      return issue.labels

   def __get_project_client(self, project=None):
      """
Get the project client for the specified project.

**Arguments:**

* ``project``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project name.

**Returns:**

* ``project_client``

  / *Type*: Project /

  The project client.
      """
      if project:
         return self.tracker_client.projects.get(f"{self.group}/{project}")
      elif self.project:
         if len(self.project) == 1:
            return self.tracker_client.projects.get(f"{self.group}/{self.project[0]}")
         else:
            raise Exception(f"More than one Gitlab project is configured, please specify the working project")
      else:
         raise Exception(f"Missing Gitlab project information")

   def connect(self, group: str, project: Union[list, str], token: str, hostname: str = "https://gitlab.com"):
      """
Connect to the Gitlab tracker.

**Arguments:**

* ``group``

  / *Condition*: required / *Type*: str /

  The group name.

* ``project``

  / *Condition*: required / *Type*: Union[list, str] /

  The project name(s).

* ``token``

  / *Condition*: required / *Type*: str /

  The access token.

* ``hostname``

  / *Condition*: optional / *Type*: str / *Default*: "https://gitlab.com" /

  The hostname of the Gitlab server.
      """
      self.group = group
      self.project = project
      if isinstance(project, list):
         self.project = project
      elif isinstance(project, str):
         self.project = [project]
      else:
         raise Exception("'project' parameter should be list of projects or string of single project")
      
      self.tracker_client = Gitlab(hostname, private_token=token)

   def get_ticket(self, id: int, project: str = None) -> Ticket:
      """
Get a ticket by its ID.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: int /

  The ID of the ticket.

* ``project``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project name.

**Returns:**

* ``ticket``

  / *Type*: Ticket /

  The ticket object.
      """
      gl_project = self.__get_project_client(project)
      issue = gl_project.issues.get(id)
      return self.__normalize_issue(issue, gl_project.name)

   def get_tickets(self, **kwargs) -> Ticket:
      """
Get tickets from the Gitlab tracker.

**Arguments:**

* ``kwargs``

  / *Condition*: optional / *Type*: dict /

  Additional keyword arguments for filtering tickets.

**Returns:**

* ``tickets``

  / *Type*: list[Ticket] /

  A list of tickets that satisfy the given conditions.
      """
      list_issues = list()
      exclude_condition = None
      if 'exclude' in kwargs:
         exclude_condition = kwargs['exclude']
         del kwargs['exclude']

      # 'assignee' is transformed to 'assignee_username' for client argument 
      if 'assignee' in kwargs:
         assignee_val  = kwargs['assignee']
         kwargs['assignee_username'] = assignee_val
         del kwargs['assignee']

      for project in self.project:
         gl_project = self.__get_project_client(project)
         issues = gl_project.issues.list(**kwargs)
         for issue in issues:
            issue = self.__normalize_issue(issue, project)
            if self.exclude_issue_by_condition(issue, exclude_condition):
               list_issues.append(issue)
      
      return list_issues

   def create_ticket(self, project: str = None, **kwargs) -> str:
      """
Create a new ticket in the Gitlab tracker.

**Arguments:**

* ``project``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project name.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for creating the ticket.

**Returns:**

* ``ticket_id``

  / *Type*: str /

  The ID of the created ticket.
      """
      gl_project = self.__get_project_client(project)
      issue = gl_project.issues.create(**kwargs)
      return issue.iid

   def update_ticket(self, id: int, project: str = None , **kwargs):
      """
Update an existing ticket in the Gitlab tracker.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: int /

  The ID of the ticket to update.

* ``project``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project name.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for updating the ticket.
      """
      gl_project = self.__get_project_client(project)
      edit_issue = gl_project.issues.get(id)
      
      for attr, val in kwargs.items():
         setattr(edit_issue, attr, val)

      edit_issue.save()

   def get_story_point(self, issue):
      """
Get the story points of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: dict /

  The issue data.

**Returns:**

* ``story_points``

  / *Type*: int /

  The story points of the issue.
      """
      # # try to get estimated time (not is used)
      # try:
      #    time_estimate = issue.time_stats()
      #    if time_estimate['time_estimate'] > 0:
      #       return self.time_estimate_to_story_point(time_estimate['time_estimate'])
      # except:
      #    pass

      # get story point from labels
      return self.get_story_point_from_labels(issue.labels)

   def create_label(self, label_name: str, color: str = None, project: str = None):
      """
Create a new label in the Gitlab tracker.

**Arguments:**

* ``label_name``

  / *Condition*: required / *Type*: str /

  The name of the label.

* ``color``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The color of the label.

* ``project``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project name.
      """
      gl_project = self.__get_project_client(project)
      list_existing_labels = gl_project.labels.list()
      for item in list_existing_labels:
         if item.name == label_name:
            return

      label_pros = {
         'name': label_name,
         'color': color if color else self.SPRINT_LABEL_COLOR
      }
      
      gl_project.labels.create(label_pros)

class RTCTracker(TrackerService):
   """
Tracker client to integrate with issues on RTC (Rational Team Concert).
   """
   TYPE = "rtc"

   def __init__(self):
      """
Initialize the RTCTracker instance.
      """
      super().__init__()
      self.project = None
      self.hostname = None
      
      self.returned_prop = ["dc:title",
                            "dc:identifier",
                            "rtc_cm:state",
                            "rtc_cm:ownedBy",
                            "dc:description",
                            "rtc_cm:teamArea",
                            "rtc_cm:com.ibm.team.workitem.attribute.storyPointsNumeric"]

   def __normalize_issue(self, issues: list) -> list[Ticket]:
      """
Normalize a list of issues to Ticket objects.

**Arguments:**

* ``issues``

  / *Condition*: required / *Type*: list /

  A list of issues to normalize.

**Returns:**

* ``tickets``

  / *Type*: list[Ticket] /

  A list of Ticket objects created from the issue data.
      """
      return [Ticket(self.TYPE,
                     issue['dcterms:identifier'],
                     issue['dcterms:title'],
                     issue['dcterms:description'],
                     issue['dcterms:contributor']['rdf:resource'],
                     issue['rdf:about'],
                     Status.normalize_issue_status(self.TYPE, issue['oslc_cm:status']),
                     story_point=issue['rtc_ext:com.ibm.team.workitem.attribute.storyPointsNumeric'],
                     version=self.get_plannedFor(issue),
                     issue_client=self.tracker_client
                     ) for issue in issues]
   
   def connect(self, project: str, hostname: str, username: Union[list, str] = None, password: str = None, token: str = None, file_against: str = None):
      """
Connect to the RTC tracker.

**Arguments:**

* ``project``

  / *Condition*: required / *Type*: str /

  The project name.

* ``hostname``

  / *Condition*: required / *Type*: str /

  The hostname of the RTC server.

* ``username``

  / *Condition*: optional / *Type*: Union[list, str] / *Default*: None /

  The username for authentication.

* ``password``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The password for authentication.

* ``token``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The token for authentication.

* ``file_against``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The file against which to authenticate.
      """
      self.project = project
      self.hostname = hostname
      self.tracker_client = RTCClient(hostname, project, username, token, file_against)

   def get_ticket(self, id: Union[str, int]) -> Ticket:
      """
Get a ticket by its ID.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: Union[str, int] /

  The ID of the ticket.

**Returns:**

* ``ticket``

  / *Type*: Ticket /

  The ticket object.
      """
      ticket = self.tracker_client.get_workitem(id)
      return self.__normalize_issue([ticket])[0]

   def get_tickets(self, **kwargs) -> list[Ticket]:
      """
Get tickets from the RTC tracker.

**Arguments:**

* ``kwargs``

  / *Condition*: optional / *Type*: dict /

  Additional keyword arguments for filtering tickets.

**Returns:**

* ``tickets``

  / *Type*: list[Ticket] /

  A list of tickets that satisfy the given conditions.
      """
      pass

   def get_plannedFor(self, issue: Ticket) -> str:
      """
Get the planned for attribute of an issue.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: Ticket /

  The issue object.

**Returns:**

* ``planned_for``

  / *Type*: str /

  The planned for attribute of the issue.
      """
      if 'rtc_cm:plannedFor' in issue and 'rdf:resource' in issue['rtc_cm:plannedFor']:
         try:
            plannedFor = self.tracker_client.get_info_from_url(issue['rtc_cm:plannedFor']['rdf:resource'], 'dcterms:title')
            return plannedFor
         except:
            return ""
      return ""

   def update_ticket_state(self, issue: Ticket, new_state: str):
      """
Update the state of a ticket.

**Arguments:**

* ``issue``

  / *Condition*: required / *Type*: Ticket /

  The issue object.

* ``new_state``

  / *Condition*: required / *Type*: str /

  The new state of the ticket.
      """
      if issue.status == Status.open:
         if new_state == Status.inProgress:
            self.tracker_client.update_workitem_action(issue.id, "startWorking")
         if new_state == Status.closed:
            self.tracker_client.update_workitem_action(issue.id, "startWorking")
            self.tracker_client.update_workitem_action(issue.id, "completeDevelopment")
            self.tracker_client.update_workitem_action(issue.id, "accept")
      elif issue.status == Status.inProgress:
         if new_state == Status.open:
            self.tracker_client.update_workitem_action(issue.id, "defer")
         if new_state == Status.closed:
            self.tracker_client.update_workitem_action(issue.id, "completeDevelopment")
            self.tracker_client.update_workitem_action(issue.id, "accept")
      elif issue.status == Status.closed:
         if new_state == Status.inProgress:
            self.tracker_client.update_workitem_action(issue.id, "reopen")
         if new_state == Status.open:
            self.tracker_client.update_workitem_action(issue.id, "reopen")
            self.tracker_client.update_workitem_action(issue.id, "defer")
      else:
         raise NotImplemented(f"Does not support status change from '{issue.status}'")

   def create_ticket(self, **kwargs) -> str:
      """
Create a new ticket in the RTC tracker.

**Arguments:**

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for creating the ticket.

**Returns:**

* ``ticket_id``

  / *Type*: str /

  The ID of the created ticket.
      """
      return self.tracker_client.create_workitem(**kwargs)

   def update_ticket(self, ticket_id: str, **kwargs):
      """
Update an existing ticket in the RTC tracker.

**Arguments:**

* ``ticket_id``

  / *Condition*: required / *Type*: str /

  The ID of the ticket to update.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  Additional keyword arguments for updating the ticket.
      """
      self.tracker_client.update_workitem(ticket_id, **kwargs)

class Tracker:
   """
Factory class for creating tracker instances.
   """

   @staticmethod
   def create(type: str, *args, **kwargs) -> TrackerService:
      """
Create a tracker instance of the specified type.

**Arguments:**

* ``type``

  / *Condition*: required / *Type*: str /

  The type of tracker to create.

* ``args``

  / *Condition*: optional / *Type*: tuple /

  Additional positional arguments for the tracker constructor.

* ``kwargs``

  / *Condition*: optional / *Type*: dict /

  Additional keyword arguments for the tracker constructor.

**Returns:**

* ``tracker``

  / *Type*: TrackerService /

  An instance of the specified tracker type.

**Raises:**

* ``NotImplementedError``

  If the specified tracker type is not supported.
      """
      trackers = Tracker.get_support_trackers()

      if type in trackers.keys():
         tracker = trackers[type](*args, **kwargs)
         return tracker
      else:
         raise NotImplementedError(f"not supported tracker '{type}'")

   @staticmethod
   def get_support_trackers() -> dict:
      """
Get a dictionary of supported tracker types and their corresponding classes.

**Returns:**

* ``trackers``

  / *Type*: dict /

  A dictionary where the keys are tracker types and the values are the corresponding tracker classes.
      """
      return {cls.TYPE: cls for cls in TrackerService.__subclasses__()}
