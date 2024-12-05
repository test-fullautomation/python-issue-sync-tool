from .rtc_client import RTCClient
from github import Github, Auth
from jira import JIRA, Issue
from gitlab import Gitlab
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union, Optional, Callable
import re

class Ticket():
   """
   Normalized Ticket with required information for syncing between trackers
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
               labels: Union[str, list] = None,
               destination_id: Optional[str] = None,
               issue_client: Callable = None):
      self.tracker = tracker
      self.id = original_id
      self.title = title
      self.description = description
      self.assignee = assignee
      self.url = url
      self.status = status
      self.createdDate = createdDate
      self.updatedDate = updatedDate
      self.component= component
      self.version = version
      self.labels = labels
      self.story_point = story_point
      self.destination_id = destination_id
      self.issue_client = issue_client

   def __repr__(self):
      """
      Return a string representation of the Ticket object.
      """
      return (f"Ticket ({self.tracker.title()}: ID={self.id}, title=\"{self.title}\")")

   def update(self, **kwargs):
      """
      Update issue on tracker with following supported attributes:
         - title
         - assignee
         - labels
      """
      if self.issue_client:
         if self.tracker == "gitlab":
            for attr, val in kwargs.items():
               setattr(self.issue_client, attr, val)
            self.issue_client.save()
         elif self.tracker == "github":
            self.issue_client.edit(**kwargs)
         elif self.tracker == "jira":
            if 'assignee' in kwargs:
               assignee_val = {"name" : kwargs['assignee']}
               kwargs['assignee'] = assignee_val
            if 'title' in kwargs:
               title_val = kwargs['title']
               kwargs['summary'] = title_val
               del kwargs['title']
            self.issue_client.update(**kwargs)
         elif self.tracker == 'rtc':
            self.issue_client.update_workitem(self.id, **kwargs)
      else:
         raise NotImplementedError(f"No implementation to update {self.tracker.title()} issue.")
   
   def is_synced_issue(self):
      """
      Verify whether the ticket is already synced or not.

      It bases on the title of issue, it should contain destination ID information.
      E.g `[ 1234 ] Title of already synced ticket`
      """
      match = re.search(r"^\[\s*(\d+)\s*\]", self.title)
      if match:
         self.destination_id = match.group(1) 
         return True
      return False
   
class TrackerService(ABC):
   """
   Abstraction class of Tracker Service
   """
   def __init__(self):
      self.tracker_client = None
   
   @abstractmethod
   def connect(self, *args, **kwargs):
      """
      Method to connect to tracker
      """
      pass
   
   @abstractmethod
   def get_ticket(self, id: Union[str, int]) -> Ticket:
      """
      Method to get single ticket by id from tracker
      """
      pass

   @abstractmethod
   def get_tickets(self, **kwargs) -> list[Ticket]:
      """
      Method to get all tickets which satisfied given condition|query
      """
      pass

   @abstractmethod
   def create_ticket(self, ticket: Ticket) -> str:
      """
      Method to create a new ticket on tracker system
      """
      pass

   def exclude_issue_by_condition(self, issue: Issue, exclude_condition=None):
      """
      Process to verify whether the given issue is satisfied the exclude conditions
      """
      if exclude_condition:
         for key, value in exclude_condition.items():
            # print(f"verify condition issue[{key}] == '{value}'")
            if key in ["assignee", "labels"]:
               if not getattr(issue, key):
                  if value == "empty": return False
               else: 
                  if (value in getattr(issue, key)): return False
            else:
               if getattr(issue, key) == value: return False
      return True

class JiraTracker(TrackerService):
   TYPE = "jira"

   def __init__(self):
      super().__init__()
      self.project = None
      self.hostname = None

   def __normalize_issue(self, issues: list):
      return [Ticket(self.TYPE,
                     issue.key,
                     issue.raw['fields']['summary'],
                     issue.raw['fields']['description'],
                     issue.raw['fields']['assignee']['name'],
                     f"{self.hostname}/browse/{issue.key}",
                     issue.raw['fields']['status']['name'],
                     issue_client=issue
                     ) for issue in issues]

   def connect(self, project: str, token: str, hostname: str):
      self.project = project
      self.hostname = hostname
      self.tracker_client = JIRA(hostname, token_auth=token)
   
   def get_ticket(self, id: str) -> Ticket:
      issue = self.tracker_client.issue(id)
      return self.__normalize_issue([issue])[0]

   def get_tickets(self, **kwargs) -> list[Ticket]:
      list_issues = list()
      jql = list()
      jql.append(f'project={self.project}')
      exclude_condition = None
      if 'exclude' in kwargs:
         exclude_condition = kwargs['exclude']
         del kwargs['exclude']
         for key, val in exclude_condition.items():
            jql.append(f"{key} not in ({','.join(val)})")

      for key, val in kwargs.items():
         jql.append(f"{key} in ({','.join(val)})")

      list_issues = self.tracker_client.search_issues(" AND ".join(jql))
      issues = self.__normalize_issue(list_issues)
      return issues

   def create_ticket(self, project: str = None, **kwargs) -> str:
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
      edit_issue = self.tracker_client.issue(id)
      edit_issue.update(**kwargs)

class GithubTracker(TrackerService):
   TYPE = "github"

   def __init__(self):
      super().__init__()
      self.repositories = list()
      self.project = None

   def __normalize_issue(self, issue: str, repo: str):
      return Ticket(self.TYPE,
                    issue.number,
                    issue.title,
                    issue.body,
                    [assignee.login for assignee in issue.assignees],
                    issue.html_url,
                    issue.state,
                    repo,
                    labels=[label.name for label in issue.labels],
                    issue_client=issue)
   
   def __get_repository_client(self, repository=None):
      if repository:
         return self.tracker_client.get_repo(f"{self.project}/{repository}")
      elif self.repositories:
         if len(self.repositories) == 1:
            return self.tracker_client.get_repo(f"{self.project}/{self.repositories[0]}")
         else:
            raise Exception(f"More than one Github repository is configured, please specify the working repository")
      else:
         raise Exception(f"Missing Github repository information")
      
   def connect(self, project: str, repository: Union[list, str], token: str, hostname: str = "api.github.com"):
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
      gh_repo = self.__get_repository_client(repository)
      return gh_repo.get_issue(id)

   def create_ticket(self, repository: str = None, **kwargs) -> str:
      gh_repo = self.__get_repository_client(repository)
      issue = gh_repo.create_issue(**kwargs)
      return issue.number

   def update_ticket(self, id: int, repository: str = None, **kwargs):
      gh_repo = self.__get_repository_client(repository)
      edit_issue = gh_repo.get_issue(id)
      edit_issue.edit(**kwargs)

class GitlabTracker(TrackerService):
   """
   Tracker client to integrate with issues on Gitlab.

   Except, `get_tickets` which allow to get issues from gitlab, group and project level,
   other method requires `project` information to interact properly with inside issues.
   """
   TYPE = "gitlab"

   def __init__(self):
      super().__init__()
      self.group = None
      self.project = None
      self.hostname = None

   def __normalize_issue(self, issue, project):
      return Ticket(self.TYPE,
                    issue.iid,
                    issue.title,
                    issue.description,
                    issue.assignee['username'],
                    issue.web_url,
                    issue.state,
                    project,
                    labels=issue.labels,
                    issue_client=issue)
   
   def __get_project_client(self, project=None):
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
      gl_project = self.__get_project_client(project)
      return gl_project.issues.get(id)

   def get_tickets(self, **kwargs) -> Ticket:
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
      gl_project = self.__get_project_client(project)
      issue = gl_project.issues.create(**kwargs)
      return issue.iid
   
   def update_ticket(self, id: int, project: str = None , **kwargs):
      gl_project = self.__get_project_client(project)
      edit_issue = gl_project.issues.get(id)
      
      for attr, val in kwargs.items():
         setattr(edit_issue, attr, val)

      edit_issue.save()
   
class RTCTracker(TrackerService):
   TYPE = "rtc"
   def __init__(self):
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

   def __normalize_issue(self, issues: list):
      return [Ticket(self.TYPE,
                     issue['dcterms:identifier'],
                     issue['dcterms:title'],
                     issue['dcterms:description'],
                     issue['dcterms:contributor']['rdf:resource'],
                     issue['rdf:about'],
                     issue['oslc_cm:status'],
                     story_point=issue['rtc_ext:com.ibm.team.workitem.attribute.storyPointsNumeric'],
                     issue_client=self.tracker_client
                     ) for issue in issues]
   
   def connect(self, project: str, hostname: str, username: Union[list, str] = None, password: str= None, token: str= None, proxy: str = None):
      self.project = project
      self.hostname = hostname
      self.tracker_client = RTCClient(hostname, project, username, token)

   def get_ticket(self, id: Union[str, int]) -> Ticket:
      ticket = self.tracker_client.get_workitem(id)
      return self.__normalize_issue([ticket])[0]

   def get_tickets(self, **kwargs) -> list[Ticket]:
      pass

   def create_ticket(self, **kwargs) -> str:
      return self.tracker_client.create_workitem(**kwargs)

   def update_ticket(self, ticket: Ticket):
      pass

class Tracker():
   SUPPORT_TRACKER = ["github", "jira", "rtc"]

   @staticmethod
   def create(type, *args, **kwargs):
      trackers = Tracker.get_support_trackers()

      if type in trackers.keys():
         tracker = trackers[type](*args, **kwargs)
         return tracker
      else:
         raise NotImplemented(f"not supported tracker '{type}'")

   @staticmethod
   def get_support_trackers():
      return {cls.TYPE : cls for cls in TrackerService.__subclasses__()}
