import requests
import copy
import urllib3
from io import BytesIO
from lxml import etree
import os
import re
from xml.sax.saxutils import escape
from collections import defaultdict, deque
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_xml_tree(file_name, bdtd_validation=True):
   """
Parse xml object from file.

**Arguments:**

* ``file_name``

  / *Condition*: required / *Type*: str /

  The name of the file to parse.

* ``bdtd_validation``

  / *Condition*: optional / *Type*: bool / *Default*: True /

  Whether to validate the XML against a DTD.

**Returns:**

* ``oTree``

  / *Type*: etree.ElementTree /

  The parsed XML tree.
   """
   oTree = None
   try:
      oParser = etree.XMLParser(dtd_validation=bdtd_validation)
      oTree = etree.parse(file_name, oParser)
   except Exception as reason:
      raise RuntimeError(f"Could not parse xml data. Reason: {reason}")
   return oTree

def escape_xml_content(content):
   """
Escape special XML characters.

**Arguments:**

* ``content``

  / *Condition*: required / *Type*: str /

  The content need to be escaped.

**Returns:**

* / *Type*: str /

  The escaped content.
   """
   entities = {
      "\u00A0": " "  # Non-breaking space &nbsp
   }
   return escape(content, entities)

class RTCClient():
   """
Client for interacting with RTC (Rational Team Concert).
   """
   itemName = "itemName/com.ibm.team.workitem.WorkItem"
   xml_attr_mapping = {
      "title": "dcterms:title",
      "description": "dcterms:description",
      "story_point": "rtc_ext:com.ibm.team.apt.attribute.complexity",
      "priority": "oslc_cmx:priority",
      "assignee": "dcterms:contributor",
      "labels": "dcterms:subject",
      "children": "rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.children",
      "parent": "rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.parent",
      "type": "rtc_cm:type",
      "epic_statement": "rtc_ext:com.ibm.team.workitem.attribute.epicHypothesisStatement",
      "project_scope": "rtc_ext:project_scope",
      "planned_for": "rtc_cm:plannedFor"
   }
   workflow_id = "com.ibm.team.apt.storyWorkflow"
   state_transition = {
      "Start Working": [ "New", "In Development"],
      "Complete Development": ["In Development", "In Test"],
      "Accept": ["In Test", "Done"],
      "Reopen": ["Done", "In Development"],
      "Reject": ["In Test", "In Development"],
      "Defer": ["In Development", "New"]
   }

   def __init__(self, hostname, project, username, token, file_against=None,
                workflow_id=None, state_transition=None, project_scope=None,
                planned_for=None):
      """
Initialize the RTCClient instance.

**Arguments:**

* ``hostname``

  / *Condition*: required / *Type*: str /

  The hostname of the RTC server.

* ``project``

  / *Condition*: required / *Type*: str /

  The project name.

* ``username``

  / *Condition*: required / *Type*: str /

  The username for authentication.

* ``token``

  / *Condition*: required / *Type*: str /

  The authentication token.

* ``file_against``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The file against which to authenticate.
      """
      self.hostname = hostname[:-1] if hostname.endswith("/") else hostname
      self.user = username
      self.project = {
         "name": project,
         "id": ""
      }
      self.file_against = file_against
      self.project_scope = project_scope
      self.planned_for = planned_for
      self.session = requests.Session()
      self.headers = {
         "Content-Type": "application/xml",
         "Accept": "application/json",
         "OSLC-Core-version": "2.0",
         "Authorization" : f"Basic {token}"
      }
      self.session.headers = self.headers
      self.templates_dir = os.path.join(os.path.dirname(__file__),'rtc-templates')

      self.login()
      self.defined_complexity = self.__get_complexity_cache()
      self.defined_priority = self.__get_priority()
      self.defined_workitem_type = self.__get_workitem_type()
      self.defined_project_scope = self.__get_project_scope()
      # self.defined_sprints = self.__get_defined_planned_for()
      if workflow_id:
         self.workflow_id = workflow_id
      if state_transition:
         self.state_transition = state_transition
      self.state_transition_graph = None

   def __get_request(self, url, resource_type, custom_headers=None, exception_on_failure=True):
      get_kwargs = {
         "allow_redirects": True,
         "verify": False
      }
      if custom_headers:
         get_kwargs['headers'] = custom_headers

      res = self.session.get(url, **get_kwargs)

      if res.status_code != 200 and exception_on_failure:
         raise Exception(f"Failed to request to get '{resource_type}', url: '{url}'")

      return res

   def __retrieve_planned_for_results(self, url):
      return_data = dict()
      res = self.session.get(url, allow_redirects=True, verify=False)

      if res.status_code != 200:
         raise Exception(f"Failed to request to get Planned_For information, url: '{url}'")

      try:
         res_json = res.json()
         for item in res_json["oslc:results"]:
            return_data[item["dcterms:title"]] = item["rdf:about"]
      except Exception as reason:
         raise Exception(f"Error when parsing Planned_For response. Reason: {reason}")

      next_page_url = res_json.get('oslc:responseInfo', {}).get('oslc:nextPage')
      if next_page_url:
         return_data.update(self.__retrieve_planned_for_results(next_page_url))

      return return_data

   def __get_defined_planned_for(self):
      url = f"{self.hostname}/ccm/oslc/iterations?oslc.select=dcterms:identifier,dcterms:title"
      return self.__retrieve_planned_for_results(url)

   def get_planned_for_url(self, name):
      if name:
         url = f"{self.hostname}/ccm/oslc/iterations?oslc.where=dcterms:title=\"{name}\"&oslc.select=dcterms:identifier,dcterms:title"
         print(url)
         res = self.__get_request(url, "Planned For")
         try:
            res_json = res.json()
            print(res_json)
            return res_json['oslc:results'][0]["rdf:about"]
         except:
            raise Exception(f"Failed to get 'Planned For' url from response {res_json}")

      return None

   def __get_project_scope(self, project_id=None):
      """
Get the defined project scope for the specified project.

**Arguments:**

* ``project_id``

   / *Condition*: optional / *Type*: str / *Default*: None /

   The project ID.

**Returns:**

* ``dict_project_scope``

   / *Type*: dict /

   A dictionary of project scopes.
      """
      if not project_id:
         if not self.project['id']:
            self.__get_projectID()
         project_id = self.project['id']

      url = f"{self.hostname}/ccm/oslc/enumerations/{project_id}/project_scope"

      res = self.session.get(url, allow_redirects=True, verify=False)

      if res.status_code != 200:
         raise Exception(f"Failed to request to get project_scope, url: '{url}'")

      dict_project_scope = dict()
      list_project_scope = res.json()['oslc:results']
      for item in list_project_scope:
         project_scope = item['dcterms:title'].lower()
         dict_project_scope[project_scope] = item['rdf:about']

      return dict_project_scope

   def get_project_scope_url(self, project_scope):
      """
Get the project scope link.

**Arguments:**

* ``project_scope``

  / *Condition*: required / *Type*: str /

  The project_scope name.

**Returns:**

* ``project_scope_url``

  / *Type*: str /

  The link to given project_scope name.
      """
      if not project_scope:
         if 'unassigned' in self.defined_project_scope:
            return self.defined_project_scope['unassigned']
         else:
            return ""

      if project_scope.lower() not in self.defined_project_scope.keys():
         raise Exception(f"Given Project Scope value '{project_scope}' is not valid, it should be in {[item for item in self.defined_project_scope.keys()]}")
      return self.defined_project_scope[project_scope.lower()]

   def __get_workitem_type(self, project_id=None):
      """
Get the defined workitem types for the specified project.

**Arguments:**

* ``project_id``

   / *Condition*: optional / *Type*: str / *Default*: None /

   The project ID.

**Returns:**

* ``dict_workitem_type``

   / *Type*: dict /

   A dictionary of workitem types.
      """
      if not project_id:
         if not self.project['id']:
            self.__get_projectID()
         project_id = self.project['id']

      url = f"{self.hostname}/ccm/oslc/types/{project_id}"

      res = self.session.get(url, allow_redirects=True, verify=False)

      if res.status_code != 200:
         raise Exception(f"Failed to request to get priority, url: '{url}'")

      dict_workitem_type = dict()
      list_workitem_type = res.json()
      for item in list_workitem_type:
         workitem_type = item['dcterms:title'].lower()
         dict_workitem_type[workitem_type] = item['rdf:about']

      return dict_workitem_type

   def __build_state_transition(self, state_transition=None):
      """
Build state transition graph from given state_transition definition.

**Arguments:**

* ``state_transition``

  / *Condition*: optional / *Type*: dict /

  The custom state transition definition.
      """
      if not state_transition:
         state_transition = self.state_transition

      transition_graph = defaultdict(list)
      for action, (from_state, to_state) in state_transition.items():
         transition_graph[from_state].append((to_state, action))

      self.state_transition_graph = transition_graph

   def __find_action_state_change(self, start_state, end_state):
      """
Get the list of action to change workitem status from start_state to end_state.

**Arguments:**

* ``start_state``

  / *Condition*: required / *Type*: str /

  The current state.

* ``end_state``

  / *Condition*: required / *Type*: str /

  The target state.

**Returns:**

* / *Type*: list /

  The sequence of actions.
      """
      queue = deque([(start_state, [])])  # (current_state, path of actions)
      visited = set()

      while queue:
         current_state, path = queue.popleft()

         if current_state == end_state:
               return path

         if current_state not in visited:
               visited.add(current_state)
               for neighbor, action in self.state_transition_graph[current_state]:
                  if neighbor not in visited:
                     queue.append((neighbor, path + [action]))
      return None

   def __get_action_identifier(self, project_id=None, workflow_id=None):
      """
Get the action identifier for changing workitem status.

**Arguments:**

* ``project_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project ID.

* ``workflow_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The using workflow ID.

**Returns:**

* ``action_identifier_dict``

  / *Type*: dict /

  A dictionary of action names and their identifiers.
      """
      if not project_id:
         project_id = self.project['id']
      if not workflow_id:
         workflow_id = self.workflow_id

      headers = copy.deepcopy(self.headers)
      del headers["OSLC-Core-version"]
      url = f"{self.hostname}/ccm/oslc/workflows/{project_id}/actions/{workflow_id}"
      res = requests.get(url, allow_redirects=True, verify=False, headers=headers)

      if res.status_code != 200:
         raise Exception(f"Failed to request to get action definition, url: '{url}'")

      action_identifier_dict = dict()
      list_action = res.json()
      for item in list_action:
         action_identifier_dict[item['dc:title']] = item['dc:identifier']

      return action_identifier_dict

   def __get_projectID(self):
      """
Get the project ID for the specified project name.
      """
      project_found = False
      res = self.session.get(self.hostname + '/ccm/process/project-areas',
                             allow_redirects=True, verify=False)

      if res.status_code == 200:
         oProjects = get_xml_tree(BytesIO(str(res.text).encode()),
                                  bdtd_validation=False)
         nsmap = oProjects.getroot().nsmap
         for oProject in oProjects.findall('jp06:project-area', nsmap):
            if oProject.attrib['{%s}name' % nsmap['jp06']] == self.project['name']:
               sProjectURL = oProject.find("jp06:url", nsmap).text
               # replace encoded uri project name by project UUID
               self.project['id'] = sProjectURL.split("/")[-1]
               project_found = True
               break
      if not project_found:
         raise Exception(f"Could not find project with name '{self.project['name']}'")

   def __get_priority(self, project_id=None):
      """
Get the priority values for the specified project.

**Arguments:**

* ``project_id``

   / *Condition*: optional / *Type*: str / *Default*: None /

   The project ID.

**Returns:**

* ``priority_dict``

   / *Type*: dict /

   A dictionary of priority values.
      """
      if not project_id:
         if not self.project['id']:
            self.__get_projectID()
         project_id = self.project['id']

      url = f"{self.hostname}/ccm/oslc/enumerations/{project_id}/priority"

      res = self.session.get(url, allow_redirects=True, verify=False)

      if res.status_code != 200:
         raise Exception(f"Failed to request to get priority, url: '{url}'")

      priority_dict = dict()
      list_priority = res.json()['oslc:results']
      for item in list_priority:
         priority = item['dcterms:title']
         # Get integer value of priority from its title
         # Unassigned
         # 5 - Very Low
         # 4 - Low
         # 3 - Medium
         # 2 - High
         # 1 - Very High
         matched_priority = re.match(r"^(\d)(\s*-\s8\w+)?", priority)
         if matched_priority:
            priority = matched_priority.group(1)

         priority_dict[priority] = item['rdf:about']

      return priority_dict

   def get_priority_link(self, priority, project_id=None):
      """
Get the priority link.

**Arguments:**

* ``priority``

  / *Condition*: required / *Type*: int /

  The priority value.

* ``project_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project ID.

**Returns:**

* ``priority_identifier``

  / *Type*: str /

  The priority link for the specified value.
      """
      if not priority:
         if 'Unassigned' in self.defined_priority:
            return self.defined_priority['Unassigned']
         else:
            return ""

      if str(priority) not in self.defined_priority.keys():
         raise Exception(f"Given priority value '{priority}' is not valid, it should be in {[item for item in self.defined_priority.keys()]}")
      return self.defined_priority[str(priority)]

   def __get_complexity_cache(self, project_id=None):
      """
Get the complexity values for the specified project, using cache if available.

**Arguments:**

* ``project_id``

   / *Condition*: optional / *Type*: str / *Default*: None /

   The project ID.

**Returns:**

* ``complexity_dict``

   / *Type*: dict /

   A dictionary of complexity values.
      """
      if not hasattr(self, '_complexity_cache'):
         self._complexity_cache = {}

      if not project_id:
         if not self.project['id']:
            self.__get_projectID()
         project_id = self.project['id']

      if project_id in self._complexity_cache:
         return self._complexity_cache[project_id]

      complexity_dict = self.__get_complexity(project_id)
      self._complexity_cache[project_id] = complexity_dict
      return complexity_dict

   def __get_complexity(self, project_id=None):
      """
Get the complexity values for the specified project.

**Arguments:**

* ``project_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project ID.

**Returns:**

* ``complexity_dict``

  / *Type*: dict /

  A dictionary of complexity values.
      """
      if not project_id:
         project_id = self.project['id']
      url = f"{self.hostname}/ccm/oslc/enumerations/{project_id}/complexity"

      res = self.session.get(url, allow_redirects=True, verify=False)

      if res.status_code != 200:
         raise Exception(f"Failed to request to get complexity, url: '{url}'")

      complexity_dict = dict()
      list_complexity = res.json()['oslc:results']
      for item in list_complexity:
         complexity_dict[item['dcterms:identifier']] = item['rdf:about']

      return complexity_dict

   def get_complexity_link(self, story_point, project_id=None):
      """
Get the complexity link for the specified story point.

**Arguments:**

* ``story_point``

  / *Condition*: required / *Type*: int /

  The story point value.

* ``project_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project ID.

**Returns:**

* ``complexity_link``

  / *Type*: str /

  The complexity link for the specified story point.
      """
      if str(story_point) not in self.defined_complexity.keys():
         raise Exception(f"Given story point value '{story_point}' is not valid, it should be in {[item for item in self.defined_complexity.keys()]}")
      return self.defined_complexity[str(story_point)]

   def __get_filedAgainst(self, url, fileAgainst_name):
      """
Get the filed against URL for the specified file against name.

**Arguments:**

* ``url``

  / *Condition*: required / *Type*: str /

  The URL to request.

* ``fileAgainst_name``

  / *Condition*: required / *Type*: str /

  The file against name.

**Returns:**

* ``fileAgainst_url``

  / *Type*: str /

  The filed against URL.
      """
      res = self.session.get(url, allow_redirects=True, verify=False)
      if res.status_code == 200:
         try:
            obj_res = res.json()
            for result in obj_res['oslc:results']:
               fileAgainst_title = None
               if 'dc:title' in result:
                  fileAgainst_title = result['dc:title']
               elif 'rtc_cm:hierarchicalName' in result:
                  fileAgainst_title = result['rtc_cm:hierarchicalName']
               if fileAgainst_name == fileAgainst_title:
                  return result['rdf:about']

            if 'oslc:responseInfo' in obj_res and 'oslc:nextPage' in obj_res['oslc:responseInfo'] and obj_res['oslc:responseInfo']['oslc:nextPage']:
               return self.__get_filedAgainst(obj_res['oslc:responseInfo']['oslc:nextPage'], fileAgainst_name)
         except Exception as reason:
            raise Exception("Error when parsing fileAgainst response")
      else:
         raise Exception(f"Failed to request to get fileAgainst, url: '{url}'")
      return None

   def get_user_link(self, user_id):
      """
Get the user link for the specified user ID.

**Arguments:**

* ``user_id``

  / *Condition*: required / *Type*: str /

  The user id on RTC.

**Returns:**

* / *Type*: str /

  The user URL.
      """
      if not user_id:
         user_id = "unassigned"
      return f"{self.hostname}/jts/users/{user_id}"

   def get_filedAgainst(self, fileAgainst_name, project_id=None):
      """
Get the filed against URL for the specified file against name.

**Arguments:**

* ``fileAgainst_name``

  / *Condition*: required / *Type*: str /

  The file against name.

* ``project_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project ID.

**Returns:**

* ``fileAgainst_url``

  / *Type*: str /

  The filed against URL.
      """
      if not project_id:
         project_id = self.project['id']
      # url = f"{self.hostname}/ccm/oslc/categories?projectURL={self.hostname}/ccm/process/project-areas/{project_id}&oslc.select=dc:title,rdfs:member,rtc_cm:hierarchicalName"
      url = f"{self.hostname}/ccm/oslc/categories?oslc.where=rtc_cm:projectArea=\"{project_id}\"&oslc.select=dc:title,rdfs:member,rtc_cm:hierarchicalName"

      fileAgainst_url = self.__get_filedAgainst(url, fileAgainst_name)
      if not fileAgainst_url:
         raise Exception(f"Could not find fileAgainst '{fileAgainst_name}'")

      return fileAgainst_url

   def get_info_from_url(self, url, info):
      """
Get the specified information from the URL.

**Arguments:**

* ``url``

  / *Condition*: required / *Type*: str /

  The URL to request.

* ``info``

  / *Condition*: required / *Type*: str /

  The information to retrieve.

**Returns:**

* ``info_value``

  / *Type*: str /

  The retrieved information value.
      """
      res = self.session.get(url, allow_redirects=True, verify=False)
      if res.status_code == 200:
         res_data = res.json()
         if info in res_data:
            return res_data[info]
         else:
            raise Exception(f"Could not get '{info}' from response of url '{url}'.")
      else:
         raise Exception(f"Request to url '{url}' unsuccessfully. Reason: {res.reason}")

   def login(self):
      """
Authenticate and establish a session with RTC.
      """
      url = f"{self.hostname}/ccm/authenticated/identity"
      response = self.session.get(url, allow_redirects=True, verify=False)
      if response.status_code == 200:
         try:
            self.__get_projectID()
         except Exception as e:
            raise Exception(f"Failed to get project ID: {e}")
      else:
         raise Exception(f"Authenticate to RTC server {self.hostname} fail. Please verify your credential.")

   def get_workitem(self, ticket_id):
      """
Get a work item by its ID.

**Arguments:**

* ``ticket_id``

  / *Condition*: required / *Type*: str /

  The ID of the work item.

**Returns:**

* ``work_item``

  / *Type*: dict /

  The work item data.
      """
      headers = copy.deepcopy(self.headers)
      req_url = f"{self.hostname}/ccm/oslc/workitems/{ticket_id}"
      response = self.session.get(req_url, headers=headers, verify=False)
      if response.status_code == 200:
         return response.json()
      else:
         raise Exception(f"Failed to retrieve issues: {ticket_id}. Reason: {response.reason}")

   def update_workitem(self, ticket_id, **kwargs):
      """
Update a work item with the specified attributes.

**Arguments:**

* ``ticket_id``

  / *Condition*: required / *Type*: str /

  The ID of the work item.

* ``kwargs``

  / *Condition*: required / *Type*: dict /

  The attributes to update.

**Returns:**

* ``None``
      """
      url = f"{self.hostname}/ccm/oslc/workitems/{ticket_id}"
      headers = copy.deepcopy(self.headers)
      headers["Accept"] = "application/xml"
      res = self.session.get(url, headers=headers, verify=False)
      if res.status_code == 200:
         oWorkItem = get_xml_tree(BytesIO(str(res.text).encode()), bdtd_validation=False)
         nsmap = oWorkItem.getroot().nsmap

         for attr, val in kwargs.items():
            if attr not in self.xml_attr_mapping:
               raise Exception(f"Does not support to update workitem '{attr}'")
            oAttr = oWorkItem.find(f"oslc_cm:ChangeRequest//{self.xml_attr_mapping[attr]}", nsmap)
            if attr == "story_point" and oAttr is not None:
               oAttr.set("{%s}resource" % nsmap['rdf'], self.get_complexity_link(val))
            elif attr == "priority":
               oAttr.set("{%s}resource" % nsmap['rdf'], self.get_priority_link(val))
            elif attr == "assignee":
               oAttr.set("{%s}resource" % nsmap['rdf'], self.get_user_link(val))
            elif attr == "labels" and isinstance(val, list):
               oAttr.clear()
               # replace spaces with underscores due to RTC tag can not contains space
               modified_val = list(map(lambda s: s.replace(" ", "_"), val))
               oAttr.text = ", ".join(modified_val)
            elif attr == "type":
               if val.lower() not in self.defined_workitem_type.keys():
                  raise Exception(f"Not support RTC workitem type {val}")
               workitem_type_url = self.defined_workitem_type[val.lower()]
               oAttr.set("{%s}resource" % nsmap['rdf'], workitem_type_url)
            elif attr == "parent":
               if val:
                  if oAttr is not None:
                     oAttr.set("{%s}resource" % nsmap['rdf'], f"{self.hostname}/ccm/resource/itemName/com.ibm.team.workitem.WorkItem/{val}")
                  else:
                     oChangeRequest = oWorkItem.find(f"oslc_cm:ChangeRequest", nsmap)
                     namespace, xml_node = self.xml_attr_mapping['parent'].split(":")
                     oParent = etree.Element(f"{{{nsmap[namespace]}}}{xml_node}", nsmap=nsmap)
                     oParent.set("{%s}resource" % nsmap['rdf'], f"{self.hostname}/ccm/resource/itemName/com.ibm.team.workitem.WorkItem/{val}")
                     oChangeRequest.append(oParent)
            elif attr == "children":
               oChangeRequest = oWorkItem.find(f"oslc_cm:ChangeRequest", nsmap)
               namespace, xml_node = self.xml_attr_mapping['children'].split(":")
               # Find and remove all existing children node then update the new one
               current_children = oChangeRequest.findall(self.xml_attr_mapping['children'], nsmap)
               if current_children is not None:
                  for child_node in current_children:
                     oChangeRequest.remove(child_node)
               if val:
                  for child in val:
                     oChild = etree.Element(f"{{{nsmap[namespace]}}}{xml_node}", nsmap=nsmap)
                     oChild.set("{%s}resource" % nsmap['rdf'], f"{self.hostname}/ccm/resource/itemName/com.ibm.team.workitem.WorkItem/{child}")
                     oChangeRequest.append(oChild)
            elif attr == "title":
               oAttr.text = val
            elif attr == "planned_for":
               if val:
                  if oAttr is not None:
                     oAttr.set("{%s}resource" % nsmap['rdf'], self.get_planned_for_url(val))
                  else:
                     oChangeRequest = oWorkItem.find(f"oslc_cm:ChangeRequest", nsmap)
                     namespace, xml_node = self.xml_attr_mapping['planned_for'].split(":")
                     oPlannedFor = etree.Element(f"{{{nsmap[namespace]}}}{xml_node}", nsmap=nsmap)
                     oPlannedFor.set("{%s}resource" % nsmap['rdf'], self.get_planned_for_url(val))
                     oChangeRequest.append(oPlannedFor)
            else:
               if oAttr is not None:
                  oAttr.clear()
                  oAttr.text = val

         update_res = self.session.put(url, allow_redirects=True, verify=False, data=etree.tostring(oWorkItem))
         if update_res.status_code not in [200, 204]:
            raise Exception(f"Failed to update work item: {ticket_id}. Reason: {update_res.reason}")
      else:
         raise Exception(f"Failed to get work item: {ticket_id} for update. Reason: {res.reason}")

   def update_workitem_state(self, ticket_id, current_state, new_state):
      """
Update the state of a work item.

**Arguments:**

* ``ticket_id``

  / *Condition*: required / *Type*: str /

  The ID of the work item.

* ``current_state``

  / *Condition*: required / *Type*: str /

  The current state of the work item.

* ``new_state``

  / *Condition*: required / *Type*: str /

  The new state of the work item.

**Returns:**

* ``None``
      """
      self.__build_state_transition()
      action_list = self.__find_action_state_change(current_state, new_state)

      if not action_list:
         raise Exception(f"Could not found the proper action to change state from '{current_state}' to '{new_state}'")

      for action in action_list:
         self.update_workitem_action(ticket_id, action)

   def update_workitem_action(self, ticket_id, action):
      """
Update the state of a work item by performing the specified action.

**Arguments:**

* ``ticket_id``

  / *Condition*: required / *Type*: str /

  The ID of the work item.

* ``action``

  / *Condition*: required / *Type*: str /

  The action to perform.

**Returns:**

* ``None``
      """
      headers = copy.deepcopy(self.headers)
      headers["Accept"] = "application/xml"
      workitem_url = f"{self.hostname}/ccm/oslc/workitems/{ticket_id}"
      res = self.session.get(workitem_url, allow_redirects=True, verify=False, headers=headers)
      if res.status_code != 200:
         raise Exception(f"Could not found workitem {ticket_id}")

      action_identifier = self.__get_action_identifier()
      if action not in action_identifier.keys():
         raise Exception(f"Could not found action '{action}'")

      action_id = action_identifier[action]
      action_res = self.session.put(f"{workitem_url}?_action={action_id}",
                                    allow_redirects=True, verify=False, headers=headers, data=res.text)
      if action_res.status_code != 200:
         raise Exception(f"Failed in requesting to change state of workitem {ticket_id}")

   def create_workitem(self, title, description, story_point=0, file_against=None,
                       assignee=None, priority=None, project_id=None,
                       project_scope=None, planned_for=None,
                       type="Story", state = "New", **kwargs):
      """
Create a new work item.

**Arguments:**

* ``title``

  / *Condition*: required / *Type*: str /

  The title of the work item.

* ``description``

  / *Condition*: required / *Type*: str /

  The description of the work item.

* ``story_point``

  / *Condition*: optional / *Type*: int / *Default*: 0 /

  The story point value.

* ``file_against``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The file against which to create the work item.

* ``assignee``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The assignee of the work item.

* ``priority``

  / *Condition*: optional / *Type*: int / *Default*: None /

  The priority of the work item.

* ``project_id``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project ID.

* ``project_scope``

  / *Condition*: optional / *Type*: str / *Default*: None /

  The project scope name.

* ``type``

  / *Condition*: optional / *Type*: str / *Default*: "Story" /

  The RTC work item type.

* ``state``

  / *Condition*: optional / *Type*: str / *Default*: "New" /

  The RTC work item status.

* ``kwargs``

  / *Condition*: optional / *Type*: dict / *Default*: None /

  Additional keyword arguments for creating the work item.

**Returns:**

* ``workitem_id``

  / *Type*: str /

  The ID of the created work item.
      """
      if not project_id:
         project_id = self.project['id']
      user_id = self.user
      hostname = self.hostname

      title = escape_xml_content(title)
      description = escape_xml_content(description)
      epic_statement= ""
      if type.lower() == "epic":
         epic_statement = f"<{self.xml_attr_mapping['epic_statement']}>{description}</{self.xml_attr_mapping['epic_statement']}>"

      # Verify RTC workitem type
      workitem_type_url = ""
      if type.lower() not in self.defined_workitem_type.keys():
         raise Exception(f"Not support RTC workitem type {type}")
      else:
         workitem_type_url = self.defined_workitem_type[type.lower()]

      # Get contributor information
      contributors = ""
      if assignee:
         contributors = f"<{self.xml_attr_mapping['assignee']} rdf:resource=\"{hostname}/jts/users/{assignee}\" />"

      # Get project_scope information
      project_scope_url = ""
      if project_scope:
         project_scope_url = self.get_project_scope_url(project_scope)
      elif self.project_scope:
         project_scope_url = self.get_project_scope_url(self.project_scope)
      else:
         # Try to get link to Unassigned project_scope if not specified
         try:
            project_scope_url = self.get_project_scope_url("unassigned")
         except:
            project_scope_url = ""
      if project_scope_url:
         project_scope = f"<{self.xml_attr_mapping['project_scope']} rdf:resource=\"{project_scope_url}\" />"
      else:
         project_scope = ""

      # Get planned_for information
      planned_for_url = ""
      if planned_for:
         planned_for_url = self.get_planned_for_url(planned_for)
      else:
         planned_for_url = self.get_planned_for_url(self.planned_for)

      if planned_for_url:
         planned_for = f"<{self.xml_attr_mapping['planned_for']} rdf:resource=\"{planned_for_url}\" />"
      else:
         planned_for = ""

      # Get priority information
      if priority:
         priority = self.get_priority_link(priority)
      else:
         # Try to get link to Unassigned priority if not specified
         try:
            priority = self.get_priority_link("Unassigned")
         except:
            priority = ""

      # Get filed against information
      if file_against:
         filed_against = self.get_filedAgainst(file_against)
      elif self.file_against:
         filed_against = self.get_filedAgainst(self.file_against)
      else:
         raise Exception("file_against is required to create RTC workitem")

      # Get complexity - story point information for story workitem
      complexity = ""
      if type.lower() == "story":
         self.get_complexity_link(story_point)
         complexity = f"<{self.xml_attr_mapping['story_point']} rdf:resource=\"{hostname}/ccm/oslc/enumerations/{project_id}/complexity/{story_point}\"/>"

      # Get tags information
      tags = ""
      if 'labels' in kwargs and kwargs['labels']:
         # replace spaces with underscores due to RTC tag can not contains space
         labels = list(map(lambda s: s.replace(" ", "_"), kwargs['labels']))
         tags = ", ".join(labels)

      # Process children/parent for workitem
      children = ""
      parent = ""
      if 'children' in kwargs and kwargs["children"]:
         workitem_ids = []
         if isinstance(kwargs['children'], str):
            workitem_ids = [kwargs['children']]
         elif isinstance(kwargs['children'], list):
            workitem_ids = kwargs['children']
         else:
            raise TypeError(f"Not support data type {type(kwargs['children'])} for 'children' param")

         for item_id in workitem_ids:
            children = children + f"<{self.xml_attr_mapping['children']} rdf:resource=\"{hostname}/ccm/resource/itemName/com.ibm.team.workitem.WorkItem/{item_id}\" />"

      if 'parent' in kwargs and kwargs["parent"]:
         parent = f"<{self.xml_attr_mapping['parent']} rdf:resource=\"{hostname}/ccm/resource/itemName/com.ibm.team.workitem.WorkItem/{kwargs['parent']}\" />"

      workitem_template = None
      with open(os.path.join(self.templates_dir ,'workitem.xml')) as fh:
         workitem_template = fh.read()

      req_payload = workitem_template.format(**locals())
      # req_payload = workitem_template.format(
      #    project_id=project_id,
      #    user_id=user_id,
      #    hostname=hostname,
      #    assignee=assignee,
      #    filed_against=filed_against,
      #    state=state,
      #    story_point=story_point,
      #    title=title,
      #    description=description
      # )
      req_url = f"{self.hostname}/ccm/oslc/contexts/{project_id}/workitems/com.ibm.team.apt.workItemType.story"

      response = requests.post(
         req_url,
         data=req_payload,
         headers=self.headers,
         verify=False
      )

      if response.status_code == 201:
         return response.json()['dcterms:identifier']
      else:
         raise Exception(f"Failed to create new RTC work item. Reason: {response.text}")
