from typing import Any, Union

class User:
   """
Class representing a user with a name and an ID.
   """
   def __init__(self, name: str, id: Union[str, dict] = None):
      """
Initialize a new User.

**Arguments:**

* ``name``

  / *Condition*: required / *Type*: str /

  The name of the user.

* ``id``

  / *Condition*: optional / *Type*: Union[str, dict] / *Default*: None /

  The ID of the user.
      """
      self.name = name
      self.id = id
   
   def __repr__(self) -> str:
      """
Return a string representation of the User object.

**Returns:**

* ``representation``

  / *Type*: str /

  A string representation of the User object.
      """
      return f"User (Name: {self.name}\nID: {self.id})"

class UserManagement:
   """
Class for managing a list of users.
   """
   def __init__(self, users: list):
      """
Initialize the UserManagement instance.

**Arguments:**

* ``users``

  / *Condition*: required / *Type*: list /

  A list of user data dictionaries.
      """
      self.list_user = []
      for item in users:
         name = item['name']
         del item['name']
         user = User(name, item)
         self.list_user.append(user)

   def get_user(self, id: str, tracker: str) -> Union[User, None]:
      """
Get a user by their ID and tracker.

**Arguments:**

* ``id``

  / *Condition*: required / *Type*: str /

  The ID of the user.

* ``tracker``

  / *Condition*: required / *Type*: str /

  The tracker type (e.g., github, rtc).

**Returns:**

* ``user``

  / *Type*: Union[User, None] /

  The user object if found, otherwise None.
      """
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