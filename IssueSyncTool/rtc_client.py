import requests
import copy
import urllib3
from io import BytesIO
from lxml import etree
import os
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_xml_tree(file_name, bdtd_validation=True):
   """
   Parse xml object from file.
   """
   oTree = None
   try:
      oParser = etree.XMLParser(dtd_validation=bdtd_validation)
      oTree = etree.parse(file_name, oParser)
   except Exception as reason:
      print("Could not parse xml data. Reason: %s"%reason)
      exit(1)
   return oTree

class RTCClient():
   itemName = "itemName/com.ibm.team.workitem.WorkItem"
   xml_attr_mapping = {
      "title": "oslc_cm:ChangeRequest//dcterms:title",
      "description": "oslc_cm:ChangeRequest//dcterms:description",
      "story_point": "oslc_cm:ChangeRequest//rtc_ext:com.ibm.team.apt.attribute.complexity",
   }
   
   def __init__(self, hostname, project, username, token, file_against=None):
      self.hostname = hostname[:-1] if hostname.endswith("/") else hostname
      self.user = username
      self.project = {
         "name": project,
         "id": ""
      }
      self.file_against = file_against
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
      self.defined_complexity = self.__get_complexity()

   def __get_projectID(self):
      bSuccess = True
      res = self.session.get(self.hostname + '/ccm/process/project-areas', 
                             allow_redirects=True, verify=False)
      
      if res.status_code == 200:
         oProjects=get_xml_tree(BytesIO(str(res.text).encode()),
                                 bdtd_validation=False)
         nsmap = oProjects.getroot().nsmap
         for oProject in oProjects.findall('jp06:project-area', nsmap):
            if oProject.attrib['{%s}name'%nsmap['jp06']] == self.project['name']:
               sProjectURL = oProject.find("jp06:url", nsmap).text
               # replace encoded uri project name by project UUID
               self.project['id'] = sProjectURL.split("/")[-1]
               bSuccess = True
               break
      if not bSuccess:
         raise Exception(f"Could not find project with name '{self.project['name']}'")

   def __get_complexity(self, project_id=None):
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
      if str(story_point) not in self.defined_complexity.keys():
         raise Exception(f"Given story point value '{story_point}' is not valid, it should be in {[item for item in self.defined_complexity.keys()]}")
      return self.defined_complexity[str(story_point)]

   def __get_filedAgainst(self, url, fileAgainst_name):
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

            if 'oslc:nextPage' in obj_res['oslc:responseInfo'] and obj_res['oslc:responseInfo']['oslc:nextPage']:
               return self.__get_filedAgainst(obj_res['oslc:responseInfo']['oslc:nextPage'], fileAgainst_name)
         except Exception as reason:
            raise Exception(f"Error when not parsing fileAgainst response")
      else:
         raise Exception(f"Failed to request to get fileAgainst, url: '{url}'")
      return None

   def get_filedAgainst(self, fileAgainst_name, project_id=None):
      if not project_id:
         project_id = self.project['id']
      url = f"{self.hostname}/ccm/oslc/categories?projectURL={self.hostname}/ccm/process/project-areas/{project_id}&oslc.select=dc:title,rdfs:member,rtc_cm:hierarchicalName"
      
      fileAgainst_url = self.__get_filedAgainst(url, fileAgainst_name)
      if not fileAgainst_url:
         raise Exception(f"Could not found fileAgainst '{fileAgainst_name}'")

      return fileAgainst_url

   def get_info_from_url(self, url, info):
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
      """Authenticate and establish a session with RTC."""
      url = f"{self.hostname}/ccm/authenticated/identity"
      response = self.session.get(url, allow_redirects=True, verify=False)
      if response.status_code == 200:
         self.__get_projectID()
      else:
         raise Exception(f"Authenticate to RTC server {self.hostname} fail. Please verify your credential.")
        
   def get_workitem(self, ticket_id):
      headers = copy.deepcopy(self.headers)
      # headers["Content-Type"] = "application/json"
      # headers["Accept"] = "application/json"
      # req_url = f"{self.hostname}/ccm/resource/{self.itemName}/{ticket_id}"
      req_url = f"{self.hostname}/ccm/oslc/workitems/{ticket_id}"
      response = self.session.get(req_url, headers=headers, verify=False)
      if response.status_code == 200:
         return response.json()
      else:
         raise Exception(f"Failed to retrieve issues: {response.status_code}")

   def update_workitem(self, ticket_id, **kwargs):
      url = f"{self.hostname}/ccm/oslc/workitems/{ticket_id}"
      headers = copy.deepcopy(self.headers)
      headers["Accept"] = "application/xml"
      res = self.session.get(url, headers=headers, verify=False)
      if res.status_code == 200:
         oWorkItem = get_xml_tree(BytesIO(str(res.text).encode()), bdtd_validation=False)
         nsmap = oWorkItem.getroot().nsmap

         for attr, val in kwargs.items():
            if attr not in self.xml_attr_mapping:
               raise Exception(f"Does not support to update workitem '{attr}")
            oAttr = oWorkItem.find(self.xml_attr_mapping[attr], nsmap)
            if attr == "story_point":
               oAttr.set("{%s}resource"%nsmap['rdf'], self.get_complexity_link(val))
            else:
               oAttr.text = val

         update_res = self.session.put(url, allow_redirects=True, verify=False, data=etree.tostring(oWorkItem))
         if update_res.status_code not in [200, 204]:
            raise Exception(f"Failed to update work item: {update_res.status_code}. Reason: {update_res.reason}")
      else:
         raise Exception(f"Failed to get work item: {update_res.status_code} for update")

   def update_workitem_state(self, ticket_id, current_state, new_state):
      # States transitions" "New" <-> "In Development" <-> "In Test" <-> "Done"

      mapping_action = {
         "startWorking": [ "New", "In Development"],
         "completeDevelopment": ["In Development", "In Test"],
         "accept": ["In Test", "Done"],
         "reopen": ["Done", "In Development"],
         "reject": ["In Test", "In Development"],
         "defer": ["In Development", "New"]
      }
      req_action = None
      for action, states in mapping_action:
         if current_state.lower() == states[0].lower() and new_state.lower() == states[1].lower():
            req_action = action
            break
      if not req_action:
         raise Exception(f"Could not found the proper action to change state from '{current_state}' to '{new_state}'")
      
      return self.update_workitem_action(ticket_id, req_action)
      
   def update_workitem_action(self, ticket_id, action):
      # print(f"update_workitem_action: {ticket_id} {action}")
      headers = copy.deepcopy(self.headers)
      headers["Accept"] = "application/xml"
      workitem_url = f"{self.hostname}/ccm/oslc/workitems/{ticket_id}"
      res = self.session.get(workitem_url, allow_redirects=True, verify=False, headers=headers)
      if res.status_code != 200:
         raise Exception(f"Could not found workitem {ticket_id}")
      
      action_res = self.session.put(f"{workitem_url}?_action=com.ibm.team.apt.storyWorkflow.action.{action}", 
                                    allow_redirects=True, verify=False, headers=headers, data=res.text)
      if action_res.status_code != 200:
         raise Exception(f"Failed in requesting to change state of workitem {ticket_id}")

   def create_workitem(self, title, description, story_point=0, file_against=None, assignee=None, project_id=None, **kwargs):
      if not project_id:
         project_id = self.project['id']
      user_id = self.user
      hostname = self.hostname
      if not assignee:
         assignee = self.user

      if file_against:
         filed_against = self.get_filedAgainst(file_against)
      elif self.file_against:
         filed_against = self.get_filedAgainst(self.file_against)
      else:
         raise Exception("file_against is required to create RTC workitem")

      state = "New"
      self.get_complexity_link(story_point)

      workitem_template = None
      with open(os.path.join(self.templates_dir ,'workitem.xml')) as fh:
         workitem_template = fh.read()

      req_payload = workitem_template.format(**locals())

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
         raise Exception(f"Failed to create RTC work item: {response.status_code}, {response.text}")

