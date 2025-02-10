import colorama as col
import json
import copy
import sys
import os
import re
from .version import VERSION, VERSION_DATE
from .utils import CONFIG_SCHEMA, REGEX_SPRINT_LABEL
from argparse import ArgumentParser
from jsonschema import validate
from .tracker import Tracker, Status
from .user import UserManagement

class Logger:
   """
Logger class for logging messages.
   """
   output_logfile = None
   output_console = True
   color_normal   = col.Fore.WHITE + col.Style.NORMAL
   color_error    = col.Fore.RED + col.Style.BRIGHT
   color_warn     = col.Fore.YELLOW + col.Style.BRIGHT
   color_reset    = col.Style.RESET_ALL + col.Fore.RESET + col.Back.RESET
   prefix_warn    = "WARN: "
   prefix_error   = "ERROR: "
   prefix_fatalerror = "FATAL ERROR: "
   prefix_all = ""
   dryrun = False

   @classmethod
   def config(cls, output_console=True, output_logfile=None, dryrun=False):
      """
Configure Logger class.

**Arguments:**

*  ``output_console``

   / *Condition*: optional / *Type*: bool / *Default*: True /

   Write message to console output.

*  ``output_logfile``

   / *Condition*: optional / *Type*: str / *Default*: None /

   Path to log file output.

*  ``dryrun``

   / *Condition*: optional / *Type*: bool / *Default*: True /

   If set, a prefix as 'dryrun' is added for all messages.

**Returns:**

(*no returns*)
      """
      cls.output_console = output_console
      cls.output_logfile = output_logfile
      cls.dryrun = dryrun
      if cls.dryrun:
         cls.prefix_all = cls.color_warn + "DRYRUN  " + cls.color_reset

   @classmethod
   def log(cls, msg='', color=None, indent=0):
      """
Write log message to console/file output.

**Arguments:**

*  ``msg``

   / *Condition*: optional / *Type*: str / *Default*: '' /

   Message which is written to output.

*  ``color``

   / *Condition*: optional / *Type*: str / *Default*: None /

   Color style for the message.

*  ``indent``

   / *Condition*: optional / *Type*: int / *Default*: 0 /

   Offset indent.

**Returns:**

(*no returns*)
      """
      if color is None:
         color = cls.color_normal
      if cls.output_console:
         print(cls.prefix_all + cls.color_reset + color + " "*indent + msg + cls.color_reset)
      if cls.output_logfile and os.path.isfile(cls.output_logfile):
         with open(cls.output_logfile, 'a') as f:
            f.write(cls.prefix_all + " "*indent + msg + "\n")
      return

   @classmethod
   def log_warning(cls, msg, indent=0):
      """
Write warning message to console/file output.

**Arguments:**

*  ``msg``

   / *Condition*: required / *Type*: str /

   Warning message which is written to output.

*  ``indent``

   / *Condition*: optional / *Type*: int / *Default*: 0 /

   Offset indent.

**Returns:**

(*no returns*)
      """
      cls.log(cls.prefix_warn+str(msg), cls.color_warn, indent)

   @classmethod
   def log_error(cls, msg, fatal_error=False, indent=0):
      """
Write error message to console/file output.

**Arguments:**

*  ``msg``

   / *Condition*: required / *Type*: str /

   Error message which is written to output.

*  ``fatal_error``

   / *Condition*: optional / *Type*: bool / *Default*: False /

   If set, tool will terminate after logging error message.

*  ``indent``

   / *Condition*: optional / *Type*: int / *Default*: 0 /

   Offset indent.

**Returns:**

(*no returns*)
      """
      prefix = cls.prefix_error
      if fatal_error:
         prefix = cls.prefix_fatalerror

      cls.log(prefix+str(msg), cls.color_error, indent)
      if fatal_error:
         cls.log(f"{sys.argv[0]} has been stopped!", cls.color_error)
         raise SystemExit(1)

def write_csv_files(filename, list_line):
   """
Write a list of lines to a CSV file.

**Arguments:**

*  ``filename``

   / *Condition*: required / *Type*: str /

   The name of the CSV file.

*  ``list_line``

   / *Condition*: required / *Type*: list /

   A list of lines to write to the CSV file.

**Returns:**

(*no returns*)
   """
   with open(filename, 'w', encoding='utf-8') as fh:
      fh.writelines(list_line)

def process_cli_argument():
   """
Create and configure the ArgumentParser instance, then process command-line arguments.

**Returns:**

* ``args``

  / *Type*: Namespace /

  The parsed command-line arguments.
   """
   cli_parser = ArgumentParser(prog="IssueSyncTool (Tickets Sync Tool)",
                               description="IssueSyncTool sync ticket|issue|workitem "+
                                           "between tracking systems such as "+
                                           "Github Issue, JIRA and IBM RTC")
   cli_parser.add_argument('--config', type=str, required=True,
                           help='path to configuration json file')
   cli_parser.add_argument('--dryrun', action="store_true",
                           help='if set, then just dump the tickets without syncing')
   cli_parser.add_argument('--csv', action="store_true",
                           help='if set, then store the sync status to csv file sync_status.csv')
   cli_parser.add_argument('--nosync', action="store_true",
                           help="If set, issues with the 'nosync' label will not be synced, "+
                                'and any previously synced issues with this label will be closed.')
   cli_parser.add_argument('--status-only', action="store_true",
                           help='If set, only update status of synced issue on destination tracker.')
   cli_parser.add_argument('-v', '--version', action='version',
                           version=f"v{VERSION} ({VERSION_DATE})",
                           help='version of the IssueSyncTool')

   return cli_parser.parse_args()

def process_configuration(path_file):
   """
Process the configuration JSON file.

**Arguments:**

*  ``path_file``

   / *Condition*: required / *Type*: str /

   The path to the configuration JSON file.

**Returns:**

* ``config``

  / *Type*: dict /

  The configuration dictionary.
   """
   # Function to resolve environment variables in a string
   def resolve_env_variables(value):
      if isinstance(value, str):
         # Match patterns like ${VAR_NAME}
         matches = re.findall(r"\$\{(.*?)\}", value)
         for match in matches:
            env_value = os.getenv(match, "")
            value = value.replace(f"${{{match}}}", env_value)
      return value

   # Recursively resolve environment variables in the JSON data
   def resolve(data):
      if isinstance(data, dict):
         return {key: resolve(value) for key, value in data.items()}
      elif isinstance(data, list):
         return [resolve(item) for item in data]
      else:
         return resolve_env_variables(data)

   if os.path.isfile(path_file):
      with open(path_file, 'r') as json_file:
         try:
            config = json.load(json_file)
         except json.JSONDecodeError as e:
            Logger.log_error(f"Error decoding JSON file: {e}", fatal_error=True)
         try:
            validate(config, CONFIG_SCHEMA)
         except Exception as reason:
            Logger.log_error(f"Invalid configuration json file. Reason: {reason}.", fatal_error=True)

      return resolve(config)
   else:
      Logger.log_error(f"Given configuration JSON is not existing: '{path_file}'.", fatal_error=True)

def process_title(title, component=None, component_mapping=None):
   """
Process title of the ticket with component mapping.

**Arguments:**

*  ``title``

   / *Condition*: required / *Type*: str /

   The issue title.

*  ``component``

   / *Condition*: optional / *Type*: str /

   The component (repository) which issue is belong to.

*  ``component_mapping``

   / *Condition*: optional / *Type*: dict /

   Component mappings for naming ticket title on destination tracker.

**Returns:**

*  ``title``

   / *Type*: str /

   The issue title for destination tracker.
   """
   # avoid unwanted destination tracker id in destination tracker title
   if re.match(r"\[ \d+ \]", title):
      title = re.sub(r"\[ \d+ \]", "", title).strip()

   # process component mapping to add prefix [ {component_name} ] to title
   if component_mapping:
      if component and component in component_mapping:
         title = f"[ {component_mapping[component]} ] {title}"

   return title

def process_new_issue(issue, des_tracker, assignee, component_mapping=None):
   """
Process to create new issue on destination tracker and update original issue's
title with destination issue's id.

- New issue's description is consist of original issue url and its description.
- Assignee is get from

**Arguments:**

*  ``issue``

   / *Condition*: required / *Type*: Issue /

   The original issue object.

*  ``des_tracker``

   / *Condition*: required / *Type*: TrackerService /

   The destination tracker service.

*  ``assignee``

   / *Condition*: required / *Type*: User /

   The assignee user object. The user who will be assigned to the new issue on the destination tracker.

*  ``component_mapping``

   / *Condition*: optional / *Type*: dict /

   Component mappings for naming ticket title on destination tracker.

**Returns:**

* ``res_id``

  / *Type*: str /

  The ID of the created issue on the destination tracker.
   """
   issue_desc = f"Original issue url: {issue.url}\n\n{issue.description}"
   des_title = process_title(issue.title, issue.component, component_mapping)

   # Auto assign when missing assignee from original ticket
   assignee_id = ""
   if assignee:
      assignee_id = assignee.id[des_tracker.TYPE]

   res_id = des_tracker.create_ticket(title=des_title,
                                      description=issue_desc,
                                      story_point=issue.story_point,
                                      assignee=assignee_id,
                                      priority=issue.priority,
                                      labels=issue.labels)

   issue.update(title=f"[ {res_id} ] {issue.title}")

   Logger.log(f"Created new {des_tracker.TYPE.title()} issue with ID {res_id}", indent=4)
   return res_id

def process_sync_issues(org_issue, org_tracker, dest_issue, des_tracker, assignee, component_mapping=None, sync_only_status=False):
   """
Update source (original) issue due to information from appropriate destination one.

Defined sync attributes:
  - `Title`: add issue ID as prefix e.g `[ 123 ] Ticket title`when creating on destination tracker
  - `Story point`: when planning existing issue on destination tracker
  - `Version`: when planning existing issue on destination tracker

Update destination issue due to information from source.

Defined sync attributes:
  - `Status`: status is synced from original ticket, not allow to update directly on destination tracker

**Arguments:**

*  ``org_issue``

   / *Condition*: required / *Type*: Issue /

   The original issue object.

*  ``org_tracker``

   / *Condition*: required / *Type*: TrackerService /

   The original tracker service.

*  ``dest_issue``

   / *Condition*: required / *Type*: Issue /

   The destination issue object.

*  ``des_tracker``

   / *Condition*: required / *Type*: TrackerService /

   The destination tracker service.

*  ``component_mapping``

   / *Condition*: optional / *Type*: dict /

   Component mappings for naming ticket title on destination tracker.

**Returns:**

(*no returns*)
   """
   dest_issue = des_tracker.get_ticket(org_issue.destination_id)
   # Update original issue
   Logger.log(f"Updating {org_issue.tracker.title()} issue {org_issue.id}:", indent=4)

   # remove existing sprint label include 'backlog'
   labels=org_issue.labels
   sprint_label = re.compile(REGEX_SPRINT_LABEL)
   updated_labels = [i for i in labels if not sprint_label.match(i) and i != 'backlog']
   if dest_issue.version:
      Logger.log(f"Adding sprint label '{dest_issue.version}'", indent=6)
      org_tracker.create_label(dest_issue.version, repository=org_issue.component)
      updated_labels = updated_labels+[dest_issue.version]
   else:
      Logger.log_warning(f"Add 'backlog' label for unplanned issue", indent=6)
      updated_labels = updated_labels+['backlog']
   org_issue.update(labels=updated_labels)

   # Update destination issue
   Logger.log(f"Updating {dest_issue.tracker.title()} issue {dest_issue.id}:", indent=4)
   if dest_issue.status != org_issue.status:
      Logger.log(f"Syncing 'Status'... (change from '{dest_issue.status}' to '{org_issue.status}')", indent=6)
      des_tracker.update_ticket_state(dest_issue, org_issue.status)

   # Auto assign when missing assignee from original ticket
   assignee_id = ""
   if assignee:
      assignee_id = assignee.id[des_tracker.TYPE]

   if not sync_only_status:
      des_title = process_title(org_issue.title, org_issue.component, component_mapping)

      if dest_issue.title != des_title:
         Logger.log(f"Syncing 'Title', 'Description', 'Labels', 'Priority', 'Assignee' and 'Story Point'", indent=6)
         des_tracker.update_ticket(dest_issue.id, title=des_title ,story_point=org_issue.story_point,
                                   labels=updated_labels, priority=org_issue.priority,
                                   assignee=assignee_id,
                                   description=f"Original issue url: {org_issue.url}\n\n{org_issue.description}")
      else:
         Logger.log(f"Syncing 'Description', 'Labels', 'Priority', 'Assignee' and 'Story Point'", indent=6)
         des_tracker.update_ticket(dest_issue.id, story_point=org_issue.story_point,
                                   labels=updated_labels, priority=org_issue.priority,
                                   assignee=assignee_id,
                                   description=f"Original issue url: {org_issue.url}\n\n{org_issue.description}")

def SyncIssue():
   """
Main function to sync issues between tracking systems.

**Returns:**

(*no returns*)
   """
   csv_content = list()
   csv_file = "sync_status.csv"
   csv_content.append("No., Ticket, Source Link, Destination ID, Stage\n")
   args = process_cli_argument()
   Logger.config(dryrun=args.dryrun)

   if args.config:
      config = process_configuration(args.config)
   else:
      Logger.log_error("Missing configuration JSON", fatal_error=True)

   # Process component mapping information
   component_mapping = None
   if 'component_mapping' in config:
      component_mapping = config['component_mapping']

   # Process destination tracker
   des_tracker = Tracker.create(config['destination'][0])
   des_tracker_params = copy.deepcopy(config['tracker'][config['destination'][0]])
   if 'condition' in des_tracker_params:
      del des_tracker_params['condition']
   des_tracker.connect(**des_tracker_params)

   user_management = UserManagement(config['user'])

   # Process source trackers
   issue_counter = 0
   for source in config['source']:
      new_issue = 0
      sync_issue = 0
      Logger.log(f"Process issues from {source.title()}:")
      tracker = Tracker.create(source)
      tracker_params = copy.deepcopy(config['tracker'][source])
      if 'condition' in tracker_params:
         del tracker_params['condition']

      tracker.connect(**tracker_params)
      list_issue = tracker.get_tickets(**config['tracker'][source]['condition'])

      for issue in list_issue:
         sync_status = "new"
         issue_counter += 1
         Logger.log(issue.__str__(), indent=2)
         assignee = None
         if isinstance(issue.assignee, str):
            assignee = user_management.get_user(issue.assignee, source)
         elif isinstance(issue.assignee, list) and len(issue.assignee):
            assignee = user_management.get_user(issue.assignee[0], source)

         if issue.is_synced_issue():
            # update original issue on source tracker with planing from destination
            try:
               dest_issue = des_tracker.get_ticket(issue.destination_id)
            except Exception:
               csv_content.append(f"{issue_counter}, {issue.tracker.title()} {issue.id}, {issue.url}, {config['destination'][0]} {issue.destination_id}, not found\n")
               Logger.log_warning(f"{config['destination'][0].title()} issue {issue.destination_id} cannot be found.", indent=4)
               continue

            if args.nosync and 'nosync' in issue.labels:
               sync_status = "closed nosync"
               if not args.dryrun:
                  Logger.log(f"Closing {dest_issue.tracker.title()} issue {dest_issue.id} due to 'nosync'", indent=4)
                  des_tracker.update_ticket_state(dest_issue, Status.closed)
            else:
               sync_status = "synced"
               if not args.dryrun:
                  process_sync_issues(issue, tracker, dest_issue, des_tracker, assignee, component_mapping, args.status_only)
            csv_content.append(f"{issue_counter}, {issue.tracker.title()} {issue.id}, {issue.url}, {config['destination'][0]} {issue.destination_id}, {sync_status}\n")
            sync_issue += 1

         else:
            res_id = ""
            if args.nosync and 'nosync' in issue.labels:
               sync_status = "nosync"
            elif args.status_only:
               sync_status = "skipped"
            else:
               # create new issue on destination tracker
               if not args.dryrun:
                  res_id = process_new_issue(issue, des_tracker, assignee, component_mapping)
               new_issue += 1

            csv_content.append(f"{issue_counter}, {issue.tracker.title()} {issue.id}, {issue.url}, {config['destination'][0]} {res_id}, {sync_status}\n")


      Logger.log(f"{new_issue + sync_issue} {source.title()} issues has been synced (includes {new_issue} new creation) to {config['destination'][0]} successfully!\n", indent=2)

   Logger.log(f"Total {issue_counter} issues has been synced to {config['destination'][0]} successfully!")
   if args.csv:
      write_csv_files(csv_file, csv_content)

if __name__ == "__main__":
   SyncIssue()