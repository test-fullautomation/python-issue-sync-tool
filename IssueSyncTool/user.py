from typing import Any, Union


class User():
   def __init__(self, name: str, id: Union[str, dict] = None):
      self.name = name
      self.id = id
   
   def  __repr__(self) -> str:
      return f"User (Name: {self.name}\nID: {self.id})"

class UserManagement():
   def __init__(self, users: list):
      self.list_user = []
      for item in users:
         name = item['name']
         del item['name']
         user = User(name, item)
         self.list_user.append(user)

   def get_user(self, id, tracker):
      for user in self.list_user:
         if (tracker in user.id) and (user.id[tracker] == id.lower()):
            return user
         
      return None

if __name__ == "__main__":
   user = User("Ngoan")
   user.id = "ntd1hc"
   user.id = {
      "github": "ngoan1608",
      "rtc": "ntd1hc"
   }

   print(user)