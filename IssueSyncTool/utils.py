CONFIG_SCHEMA = {
   "type": "object",
   "properties": {
      "source": {
         "minItems": 1,
         "$ref": "#/$defs/array_of_string"
      },
      "destination": {
         "minItems": 1,
         "$ref": "#/$defs/array_of_string"
      },
      "user": {
         "type": "array",
         "items": {
               "type": "object",
               "properties": {
                  "name": {"type": "string"},
                  "github": {"type": "string"},
                  "jira": {"type": "string"},
                  "rtc": {"type": "string"}
               },
               "required": ["name"]
            }
      },
      "tracker": {
         "type": "object",
         "properties": {
            "github": {
               "type": "object",
               "properties": {
                  "project": {"type": "string"},
                  "token": {"type": "string"},
                  "repository" : {
                     "minItems": 1,
                     "$ref": "#/$defs/array_of_string"
                  },
                  "condition": {
                     "$ref": "#/$defs/github_condition",
                     "exclude": {
                        "$ref": "#/$defs/github_condition",
                     }
                  }
               },
               "required": ["project", "repository", "token"],
               "additionalProperties": False
            },
            "gitlab": {
               "type": "object",
               "properties": {
                  "hostname": {"type": "string"},
                  "token": {"type": "string"},
                  "group": {"type": "string"},
                  "project" : {
                     "minItems": 1,
                     "$ref": "#/$defs/array_of_string"
                  },
                  "condition": {
                     "$ref": "#/$defs/gitlab_condition",
                     "exclude": {
                        "$ref": "#/$defs/gitlab_condition",
                     }
                  }
               },
               "required": ["project", "group", "token"],
               "additionalProperties": False
            },
            "jira": {
               "type": "object",
               "properties": {
                  "hostname": {"type": "string"},
                  "project": {"type": "string"},
                  "token": {"type": "string"},
                  "condition": {
                     "$ref": "#/$defs/jira_condition",
                     "exclude": {
                        "$ref": "#/$defs/jira_condition",
                     }
                  }
               },
               "required": ["hostname", "project", "token"],
               "additionalProperties": False
            },
            "rtc": {
               "type": "object",
               "properties": {
                  "hostname": {"type": "string"},
                  "project": {"type": "string"},
                  "password": {"type": "string"},
                  "username": {"type": "string"},
                  "token": {"type": "string"},
                  "proxy": {"type": "string"},
                  "condition": {
                     "$ref": "#/$defs/rtc_condition",
                     "exclude": {
                        "$ref": "#/$defs/rtc_condition",
                     }
                  }
               },
               "required": ["hostname", "project"],
               "additionalProperties": False
            }
         }
      }
   },
   "required": ["source", "destination", "tracker"],
   "additionalProperties": False,
   "$defs": {
      "array_of_string": {
         "type": "array",
         "items": {"type": "string"},
         "additionalItems": False
      },
      "github_condition": {
         "type": "object",
         "properties": {
            "labels" : {
               "type": "array",
               "items": {"type": "string"},
               "additionalItems": False
            },
            "assignee" : { "type": "string" },
            "state" : { 
               "type": "string",
               "enum": ["open", "closed", "all"]
            }
         }
      },
      "gitlab_condition": {
         "type": "object",
         "properties": {
            "labels" : {
               "type": "array",
               "items": {"type": "string"},
               "additionalItems": False
            },
            "assignee" : { "type": "string" },
            "state" : { 
               "type": "string",
               "enum": ["opened", "closed", "all"]
            }
         }
      },
      "jira_condition": {
         "type": "object",
         "properties": {
            "labels" : {
               "$ref": "#/$defs/array_of_string"
            },
            "status" : {
               "$ref": "#/$defs/array_of_string"
            },
            "assignee" : {
               "$ref": "#/$defs/array_of_string"
            }
         }
      },
      "rtc_condition": {
         "type": "object",
         "properties": {
            "version" : {
               "$ref": "#/$defs/array_of_string"
            },
            "team" : {
               "$ref": "#/$defs/array_of_string"
            },
            "user" : {
               "$ref": "#/$defs/array_of_string"
            }
         }
      }
   }
}