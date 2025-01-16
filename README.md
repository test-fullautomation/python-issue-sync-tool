# IssueSyncTool Description

The **IssueSyncTool** provides ability synchronize issues across
multiple project management platforms (tracker) like GitHub, Jira,
GitLab, and RTC.

It facilitates seamless integration of issue tracking and planning
workflows, ensuring data consistency and efficient project management.

**IssueSyncTool** tool is operating system independent and only works
with Python 3.

## How to install

**IssueSyncTool** can be installed in two different ways.

1.  Installation via PyPi (recommended for users)

    ``` 
    pip install IssueSyncTool
    ```

    [IssueSyncTool in
    PyPi](https://pypi.org/project/python-issue-sync-tool/)

2.  Installation via GitHub (recommended for developers)

    -   Clone the **python-issue-sync-tool** repository to your machine.

        ``` 
        git clone https://github.com/test-fullautomation/python-issue-sync-tool.git
        ```

        [IssueSyncTool in
        GitHub](https://github.com/test-fullautomation/python-issue-sync-tool)

    -   Install dependencies

        **IssueSyncTool** requires some additional Python libraries.
        Before you install the cloned repository sources you have to
        install the dependencies manually. The names of all related
        packages you can find in the file `requirements.txt` in the
        repository root folder. Use pip to install them:

        ``` 
        pip install -r ./requirements.txt
        ```

        Additionally install **LaTeX** (recommended: TeX Live). This is
        used to render the documentation.

    -   Configure dependencies

        The installation of **IssueSyncTool** includes to generate the
        documentation in PDF format. This is done by an application
        called **GenPackageDoc**, that is part of the installation
        dependencies (see `requirements.txt`).

        **GenPackageDoc** uses **LaTeX** to generate the documentation
        in PDF format. Therefore **GenPackageDoc** needs to know where
        to find **LaTeX**. This is defined in the **GenPackageDoc**
        configuration file

        ``` 
        packagedoc\packagedoc_config.json
        ```

        Before you start the installation you have to introduce the
        following environment variable, that is used in
        `packagedoc_config.json`:

        -   `GENDOC_LATEXPATH` : path to `pdflatex` executable

    -   Use the following command to install **IssueSyncTool**:

        ``` 
        python setup.py install
        ```

After succesful installation, the executable file **IssueSyncTool** will
be available (under *Scripts* folder of Python on Windows and
*\~/.local/bin/* folder on Linux).

In case above location is added to **PATH** environment variable then
you can run it directly as operation system\'s command.

## How to use

**IssueSyncTool** tool requires the configuration JSON file to define
the tracker connections and conditions (queries) for sync.

Use below command to get tools\'s usage:

    IssueSyncTool -h

The usage should be showed as below:

    usage: IssueSyncTool (Tickets Sync Tool) [-h] --config CONFIG [--dryrun] [--csv] [-v]

    IssueSyncTool sync ticket|issue|workitem between tracking systems such as Github Issue, JIRA and IBM RTC

    optional arguments:
    -h, --help       show this help message and exit
    --config CONFIG  path to configuration json file
    --dryrun         if set, then just dump the tickets without syncing
    --csv            if set, then store the sync status to csv file sync_status.csv
    -v, --version    version of the IssueSyncTool

### Example

Sample configuration JSON [sync_config.json]{.title-ref} to sync issues
from Github and JIRA to RTC:

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

Execute the **IssueSyncTool** with about configuration file. :

    IssueSyncTool --config sync_config.json

### Sourcecode Documentation

To understand more detail about the tool\'s features and how to define
the proper configuration file, please refer to [IssueSyncTool tool's
Documentation](https://github.com/test-fullautomation/python-issue-sync-tool/blob/develop/IssueSyncTool/IssueSyncTool.pdf).

## Feedback

To give us a feedback, you can send an email to [Thomas
Pollerspöck](mailto:Thomas.Pollerspoeck@de.bosch.com).

In case you want to report a bug or request any interesting feature,
please don\'t hesitate to raise a ticket.

## Maintainers

[Thomas Pollerspöck](mailto:Thomas.Pollerspoeck@de.bosch.com)

[Tran Duy Ngoan](mailto:Ngoan.TranDuy@vn.bosch.com)

## Contributors

## License

Copyright 2020-2024 Robert Bosch GmbH

Licensed under the Apache License, Version 2.0 (the \"License\"); you
may not use this file except in compliance with the License. You may
obtain a copy of the License at

> [![License: Apache
> v2](https://img.shields.io/pypi/l/robotframework.svg)](http://www.apache.org/licenses/LICENSE-2.0.html)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an \"AS IS\" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
