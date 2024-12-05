import requests
import copy
import urllib3
from io import BytesIO
from lxml import etree
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
   rtc_payload="""
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:rtc_ext="http://jazz.net/xmlns/prod/jazz/rtc/ext/1.0/" xmlns:oslc="http://open-services.net/ns/core#" xmlns:acp="http://jazz.net/ns/acp#"
   xmlns:oslc_cm="http://open-services.net/ns/cm#" xmlns:oslc_cmx="http://open-services.net/ns/cm-x#" xmlns:oslc_pl="http://open-services.net/ns/pl#" xmlns:acc="http://open-services.net/ns/core/acc#" xmlns:rtc_cm="http://jazz.net/xmlns/prod/jazz/rtc/cm/1.0/"
   xmlns:process="http://jazz.net/ns/process#">
   <rdf:Description rdf:nodeID="A0">
      <dcterms:title rdf:parseType="Literal">{title}</dcterms:title>
      <rtc_ext:com.ibm.team.workitem.attribute.storyPointsNumeric rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">{story_point}</rtc_ext:com.ibm.team.workitem.attribute.storyPointsNumeric>
      <dcterms:contributor rdf:resource="{hostname}/jts/users/{assignee}" />
      <dcterms:description rdf:parseType="Literal">{description}</dcterms:description>
      <oslc_cm:status rdf:datatype="http://www.w3.org/2001/XMLSchema#string">{state}</oslc_cm:status>
      <rtc_ext:contextId rdf:datatype="http://www.w3.org/2001/XMLSchema#string">{project_id}</rtc_ext:contextId>
      <rtc_cm:subscribers rdf:resource="{hostname}/jts/users/{user_id}" />
      <rtc_cm:type rdf:resource="{hostname}/ccm/oslc/types/{project_id}/com.ibm.team.apt.workItemType.story" />
      <rtc_cm:repository rdf:resource="{hostname}/ccm/oslc/repository" />
      <rtc_cm:filedAgainst rdf:resource="{hostname}/ccm/resource/itemOid/com.ibm.team.workitem.Category/_Oz1a_XSkEe-1dO3tmL5PWA" />
      <acp:accessControl rdf:resource="{hostname}/ccm/oslc/access-control/{project_id}" />
      <oslc_cmx:project rdf:resource="{hostname}/ccm/oslc/projectareas/{project_id}" />
      <oslc:serviceProvider rdf:resource="{hostname}/ccm/oslc/contexts/{project_id}/workitems/services" />
      <process:projectArea rdf:resource="{hostname}/ccm/process/project-areas/{project_id}" />
      <dcterms:creator rdf:resource="{hostname}/jts/users/{user_id}" />
   </rdf:Description>
</rdf:RDF>"""

   def __init__(self, hostname, project, username, token):
      self.hostname = hostname
      self.user = username
      self.project = {
         "name": project,
         "id": ""
      }
      self.session = requests.Session()
      self.headers = {
         "Content-Type": "application/xml", 
         "Accept": "application/json",
         "OSLC-Core-version": "2.0",
         "Authorization" : f"Basic {token}"
      }
      self.session.headers = self.headers
      
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

   def create_workitem(self, title, description, assignee=None, project_id=None, **kwargs):
      if not project_id:
         project_id = self.project['id']
      user_id = self.user
      hostname = self.hostname
      if not assignee:
         assignee = self.user

      state = "New"
      story_point = "0"
      req_payload = self.rtc_payload.format(**locals())

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

if __name__ == "__main__":
   rtc = RTCClient("https://rb-alm-20-d.de.bosch.com", "GM-VCU_old", "ntd1hc", "bnRkMWhjOk1hdGtoYXVtb2lUMTAyMDI0")
   res = rtc.get_workitem(619562)
   print(res)
   id = rtc.create_workitem("Imported workitem by sync-tool",
                            "Ticket content")
   print(id)