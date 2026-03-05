.. Copyright 2020-2026 Robert Bosch GmbH

.. Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

.. http://www.apache.org/licenses/LICENSE-2.0

.. Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

IssueSyncTool Description
=========================

The **IssueSyncTool** provides ability synchronize issues across multiple project management 
platforms (tracker) like GitHub, Jira, GitLab, and RTC. 

It facilitates seamless integration of issue tracking and planning workflows, 
ensuring data consistency and efficient project management.

**IssueSyncTool** tool is operating system independent and only works with
Python 3.

How to install
--------------

**IssueSyncTool** can be installed in two different ways.

1. Installation via PyPi (recommended for users)

   .. code::

      pip install IssueSyncTool

   `IssueSyncTool in PyPi <https://pypi.org/project/IssueSyncTool/>`_

2. Installation via GitHub (recommended for developers)

   * Clone the **IssueSyncTool** repository to your machine.

     .. code::

        git clone https://github.com/test-fullautomation/python-issue-sync-tool.git

     `IssueSyncTool in GitHub <https://github.com/test-fullautomation/python-issue-sync-tool>`_

   * Use the following command to install **IssueSyncTool** (executed in repository main folder):

     .. code::

        python -m pip install .

     Or:

     .. code::

        python -m pip install --proxy <proxy> .

     This command will also download and install all dependencies that are required to work with the source files in the current repository.
     After the initial installation of **IssueSyncTool** is done, you have the following two possibilities:

     1. *Clean the previous installation*:

        .. code::

           python "./cleanup_installation.py"

        ``cleanup_installation.py`` explicitly deletes all files and folders within the component installation folder under
        ``site-packages`` and also deletes local build artefacts.

     2. *Render the component documentation*:

        .. code::

           python "./genpackagedoc.py"

        This would e.g. be required in case of changes in the interface of **IssueSyncTool**.

        The documentation is rendered by a separate application called **GenPackageDoc**, that is part
        of the build dependencies and runtime dependencies of **IssueSyncTool**.

        **GenPackageDoc** needs to be configured. Details about how to do this, can be found in the
        `README.rst <https://github.com/test-fullautomation/python-genpackagedoc/blob/develop/README.rst>`_
        (sections *Install dependencies* and *Configure dependencies*).

   * Use the following command to build **IssueSyncTool** (executed in repository main folder):

     .. code::

        python -m build .

     Or:

     .. code::

        python -m pip config set global.proxy <proxy>
        python -m build .

After succesful installation, the executable file **IssueSyncTool**
will be available (under ``Scripts`` folder of Python on Windows
and ``~/.local/bin/`` folder on Linux).

In case above location is added to ``PATH`` environment variable
then you can run it directly as operation system's command.

How to use
----------

**IssueSyncTool** tool requires the configuration JSON file to define the tracker connections
and conditions (queries) for sync.

Use below command to get tools's usage:

::

   IssueSyncTool -h

The usage should be showed as below:

::

   usage: IssueSyncTool (Tickets Sync Tool) [-h] --config CONFIG [--dryrun] [--csv] [-v]

   IssueSyncTool sync ticket|issue|workitem between tracking systems such as Github Issue, JIRA and IBM RTC

   optional arguments:
   -h, --help       show this help message and exit
   --config CONFIG  path to configuration json file
   --dryrun         if set, then just dump the tickets without syncing
   --csv            if set, then store the sync status to csv file sync_status.csv
   -v, --version    version of the IssueSyncTool

Example
~~~~~~~

Sample configuration JSON `sync_config.json` to sync issues from Github and JIRA to RTC:

::

   {
      "source": ["github", "jira"],
      "destination": ["rtc"],
      "tracker": {
         "github": {
            "project" : "test-fullautomation",
            "token": "<your_github_token>",
            "repository": [
               "python-issue-sync-tool",
               "RobotFramework_AIO"
            ],
            "condition": {
               "state": "open"
            }
         },
         "jira": {
            "hostname": "https://<your-jira-host>",
            "project": "<your_project_name>",
            "token": "<your_jira_token>",
            "condition": {
               "status": [ "open" ],
               "assignee": ["ntd1hc"]
            }
         },
         "rtc": {
            "hostname": "https://<your-rtc-host>",
            "project" : "<your_project_name>",
            "token": "<your_base64_token>",
            "username": "ntd1hc"
         }
      },
      "user": [
         {
            "name": "Tran Duy Ngoan",
            "github": "ngoan1608",
            "jira": "ntd1hc",
            "rtc": "ntd1hc"
         }
      ]
   }

Execute the **IssueSyncTool** with about configuration file.
::

   IssueSyncTool --config sync_config.json

Sourcecode Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

To understand more detail about the tool's features and how to define the proper configuration file, 
please refer to `IssueSyncTool tool’s Documentation`_.

Feedback
--------

To give us a feedback, you can send an email to `Thomas Pollerspöck`_.

In case you want to report a bug or request any interesting feature,
please don't hesitate to raise a ticket.

Maintainers
-----------

`Thomas Pollerspöck`_

`Tran Duy Ngoan`_

Contributors
------------



License
-------

Copyright 2020-2024 Robert Bosch GmbH

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    |License: Apache v2|

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


.. |License: Apache v2| image:: https://img.shields.io/pypi/l/robotframework.svg
   :target: http://www.apache.org/licenses/LICENSE-2.0.html
.. _IssueSyncTool tool’s Documentation: https://github.com/test-fullautomation/python-issue-sync-tool/blob/develop/IssueSyncTool/IssueSyncTool.pdf
.. _Thomas Pollerspöck: mailto:Thomas.Pollerspoeck@de.bosch.com
.. _Tran Duy Ngoan: mailto:Ngoan.TranDuy@vn.bosch.com
