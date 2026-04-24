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
                  "board_id": {"type": ["integer", "string"]},
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
                  "file_against": {"type": "string"},
                  "project_scope": {"type": "string"},
                  "planned_for": {"type": "string"},
                  "workflow_id": {"type": "string"},
                  "state_transition": {"type": "object"},
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
      },
      "component_mapping": {
         "type": "object"
      },
      "sprint_version_mapping": {
         "type": "object"
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
      "string_or_array": {
         "oneOf": [
            {
               "type": "array",
               "items": {"type": "string"},
            },
            {
               "type": "string",
            }
         ]
      },
      "github_condition": {
         "type": "object",
         "properties": {
            "labels" : {
               "$ref": "#/$defs/string_or_array"
            },
            "assignee" : {
               "$ref": "#/$defs/string_or_array"
            },
            "state" : {
               "oneOf": [
                  {
                     "type": "array",
                     "items": {
                        "type": "string",
                        "enum": ["open", "closed", "all"]
                     },
                  },
                  {
                     "type": "string",
                     "enum": ["open", "closed", "all"]
                  }
               ]
            }
         }
      },
      "gitlab_condition": {
         "type": "object",
         "properties": {
            "labels" : {
               "$ref": "#/$defs/string_or_array"
            },
            "assignee" : {
               "$ref": "#/$defs/string_or_array"
            },
            "state" : {
               "oneOf": [
                  {
                     "type": "array",
                     "items": {
                        "type": "string",
                        "enum": ["opened", "closed", "all"]
                     },
                  },
                  {
                     "type": "string",
                     "enum": ["opened", "closed", "all"]
                  }
               ]
            }
         }
      },
      "jira_condition": {
         "type": "object",
         "properties": {
            "labels" : {
               "$ref": "#/$defs/string_or_array"
            },
            "status" : {
               "oneOf": [
                  {
                     "type": "array",
                     "items": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Resolved", "Closed"]
                     },
                  },
                  {
                     "type": "string",
                     "enum": ["Open", "In Progress", "Resolved", "Closed"]
                  }
               ]
            },
            "assignee" : {
               "$ref": "#/$defs/string_or_array"
            },
            "type" : {
               "oneOf": [
                  {
                     "type": "array",
                     "items": {
                        "type": "string",
                        "enum": ["Epic", "Story", "Bug", "Change Request", "OPL", "Support Request"]
                     },
                  },
                  {
                     "type": "string",
                     "enum": ["Epic", "Story", "Bug", "Change Request", "OPL", "Support Request"]
                  }
               ]
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

REGEX_SPRINT_LABEL = r"PI.*"

REGEX_VERSION_LABEL = r"^\d+\.\d+\.\d+$"

REGEX_PRIORITY_LABEL = r"prio\s*(\d+)"

REGEX_STORY_POINT_LABEL = r"(\d+)\s*pts"

REGEX_SPRINT_BACKLOG = r"[Bb]acklog.*"