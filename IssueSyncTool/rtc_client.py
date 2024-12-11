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

   def _get_filedAgainst(self, url, fileAgainst_name):
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
               return self._get_filedAgainst(obj_res['oslc:responseInfo']['oslc:nextPage'], fileAgainst_name)
         except Exception as reason:
            raise Exception(f"Error when not parsing fileAgainst response")
      else:
         raise Exception(f"Failed to request to get fileAgainst, url: '{url}'")
      return None

   def get_filedAgainst(self, fileAgainst_name, project_id=None):
      if not project_id:
         project_id = self.project['id']
      url = f"{self.hostname}/ccm/oslc/categories?projectURL={self.hostname}/ccm/process/project-areas/{project_id}&oslc.select=dc:title,rdfs:member,rtc_cm:hierarchicalName"
      
      fileAgainst_url = self._get_filedAgainst(url, fileAgainst_name)
      if not fileAgainst_url:
         raise Exception(f"Could not found fileAgainst '{fileAgainst_name}'")

      return fileAgainst_url

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
      response = requests.get(req_url, headers=headers, verify=False)
      if response.status_code == 200:
         return response.json()
      else:
         raise Exception(f"Failed to retrieve issues: {response.status_code}")

   def update_workitem(self, ticket_id, **kwargs):
      url = f"{self.hostname}/ccm/oslc/workitems/{ticket_id}"
      updates = {}
      response = self.session.put(url, json=updates, headers=self.headers)
      if response.status_code in [200, 204]:
            print("Work item updated successfully.")
      else:
            raise Exception(f"Failed to update work item: {response.status_code}")

   def create_workitem(self, title, description, file_against=None, assignee=None, project_id=None, **kwargs):
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
      story_point = "0"

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

