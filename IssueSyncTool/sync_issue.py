import colorama as col
import json
import copy
import sys
import os
from .version import VERSION, VERSION_DATE
from .utils import CONFIG_SCHEMA
from argparse import ArgumentParser
from jsonschema import validate
from .tracker import Tracker
from .user import UserManagement

class Logger():
   """
Logger class for logging message.
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
      if color==None:
         color = cls.color_normal
      if cls.output_console:
         print(cls.prefix_all + cls.color_reset + color + " "*indent + msg + cls.color_reset)
      if cls.output_logfile!=None and os.path.isfile(cls.output_logfile):
         with open(cls.output_logfile, 'a') as f:
            f.write(" "*indent + msg)
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
         exit(1)

def write_csv_files(filename, list_line):
   with open(filename, 'w') as fh:
      fh.writelines(list_line)

def process_cli_argument():
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
   cli_parser.add_argument('-v', '--version', action='version',
                           version=f"v{VERSION} ({VERSION_DATE})",
                           help='version of the IssueSyncTool')

   return cli_parser.parse_args()

def process_configuration(path_file):
   if os.path.isfile(path_file):
      with open(path_file, 'r') as json_file:
         config = json.load(json_file)
         try:
            validate(config, CONFIG_SCHEMA)
         except Exception as reason:
            Logger.log_error(f"Invalid configuration json file. Reason: {reason}.", fatal_error=True)

      return config
   else:
      Logger.log_error(f"Given configuration JSON is not existing: '{path_file}'.", fatal_error=True)

def sync_data(source_issue, dest_issue):
   """
   Update source (original) issue due to information from appropriate destination one.

   Defined sync attributes:
     - `Title`: add issue ID as prefix e.g `[ 123 ] Ticket title`when creating on destination tracker
     - `Story point`: when planning existing issue on destination tracker
     - `Version`: when planning existing issue on destination tracker

   Update destination issue due to information from source.

   Defined sync attributes:
     - `Status`: status is synced from original ticket, not allow to update directly on destination tracker
   """
   pass

def SyncIssue():
   csv_content = list()
   csv_file = "sync_status.csv"
   csv_content.append("No., Ticket, Source Link, Destination ID, Stage\n")
   args = process_cli_argument()
   Logger.config(dryrun=args.dryrun)

   if args.config:
      config = process_configuration(args.config)
   else:
      Logger.log_error("Missing configuration JSON", fatal_error=True)

   # Process destination tracker
   des_tracker = Tracker.create(config['destination'][0])
   des_tracker_params = copy.deepcopy(config['tracker'][config['destination'][0]])
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
      del tracker_params['condition']

      tracker.connect(**tracker_params)
      list_issue = tracker.get_tickets(**config['tracker'][source]['condition'])

      for issue in list_issue:
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
               csv_content.append(f"{issue_counter}, {issue.tracker.title()} {issue.id}, {issue.url}, {config['destination'][0]} {issue.destination_id}, synced\n")
               # Update source issue
               Logger.log(f"Updating {source.title()} issue {issue.id} (under develop) ... ", indent=4)
               # Update destination issue
               Logger.log(f"Updating {config['destination'][0].title()} issue {issue.destination_id} (under develop) ... ", indent=4)
               sync_issue += 1
            except Exception:
               csv_content.append(f"{issue_counter}, {issue.tracker.title()} {issue.id}, {issue.url}, {config['destination'][0]} {issue.destination_id}, not found\n")
               Logger.log_warning(f"{config['destination'][0].title()} issue {issue.destination_id} cannot be found.", indent=4)
            
         else:
            res_id = ""
            # create new issue on destination tracker
            if not args.dryrun:
               res_id = des_tracker.create_ticket(title=issue.title,
                                                  description=f"Original issue url: {issue.url}\n\n{issue.description}",
                                                  assignee=assignee.id[config['destination'][0]])
               
               issue.update(title=f"[ {res_id} ] {issue.title}")
               Logger.log(f"Created new {config['destination'][0].title()} issue with ID {res_id}", indent=4)

            csv_content.append(f"{issue_counter}, {issue.tracker.title()} {issue.id}, {issue.url}, {config['destination'][0]} {res_id}, new\n")
            new_issue += 1

      Logger.log(f"{new_issue + sync_issue} {source.title()} issues has been synced (includes {new_issue} new creation) to {config['destination'][0]} successfully!\n", indent=2)      
   
   Logger.log(f"Total {issue_counter} issues has been synced to {config['destination'][0]} successfully!")
   if args.csv:
      write_csv_files(csv_file, csv_content)

if __name__ == "__main__":
   SyncIssue()

