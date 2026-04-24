import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))
from IssueSyncTool.user import User, UserManagement

user = User("Ngoan")
user.id = "ntd1hc"
user.id = {
   "github": "ngoan1608",
   "rtc": "ntd1hc"
}
print(user)

users_config = [
   {
      "name": "Tran Duy Ngoan",
      "github": "ngoan1608",
      "jira": "ntd1hc",
      "gitlab": "ntd1hc",
      "rtc": "ntd1hc"
   },
   {
      "name": "Mai Dinh Nam Son",
      "github": "namsonx",
      "jira": "mas2hc",
      "gitlab": "mas2hc",
      "rtc": "mas2hc"
   },
   {
      "name": "Mai Minh Tri",
      "github": "trimai3001",
      "jira": "mar3hc",
      "gitlab": "mar3hc",
      "rtc": "mar3hc"
   },
   {
      "name": "Pollerspoeck Thomas",
      "github": "test-fullautomation",
      "jira": "pol2hi",
      "gitlab": "pol2hi",
      "rtc": "pol2hi"
   },
   {
      "name": "Queckenstedt Holger",
      "github": "HolQue",
      "jira": "qth2hi",
      "gitlab": "qth2hi",
      "rtc": "qth2hi"
   },
   {
      "name": "Nguyen Huynh Tri Cuong",
      "github": "milanac030988",
      "jira": "ugc1hc",
      "gitlab": "ugc1hc",
      "rtc": "ugc1hc"
   },
   {
      "name": "Hua Van Thong",
      "github": "huavanthong",
      "jira": "htv3hc",
      "gitlab": "htv3hc",
      "rtc": "htv3hc"
   }
]
directory = UserManagement(users_config)
cur_user = directory.get_user("HolQue", "github")
print(cur_user)