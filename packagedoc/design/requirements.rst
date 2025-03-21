General requirements:
---------------------
- Sync issues from Github, Gitlab, Jira to RTC

  + Create new ticket on RTC
  + Update existing tickets on original trackers
  + Sync planing from RTC to original trackers

- Trackers (authentications, projects,...) are configurable in JSON file

- Filter|Condition|Query to select tickets are configurable in for each tracker in JSON file.
  Support negative (NOT, !) Condition

Details:
--------
1. Sync data: attributes

   +------------------+-----------+----------------------+-----------------------------------+
   | Original tracker | Direction | Destination tracker  | Stage                             |
   +==================+===========+======================+===================================+
   | Title            |     ->    | Title                | New/Sync                          |
   +------------------+-----------+----------------------+-----------------------------------+
   | Assignee         |     ->    | Assignee             | New/Sync                          |
   +------------------+-----------+----------------------+-----------------------------------+
   | URL+ Description |     ->    | Description          | New/Sync                          |
   +------------------+-----------+----------------------+-----------------------------------+
   | Status           |     ->    | Status               | New/Sync                          |
   +------------------+-----------+----------------------+-----------------------------------+
   | Story point      |     ->    | Story point          | New/Sync                          |
   +------------------+-----------+----------------------+-----------------------------------+
   | Priority         |     ->    | Priority             | New/Sync (not set on Destination) |
   +------------------+-----------+----------------------+-----------------------------------+
   | Priority         |     <-    | Priority             | Sync (is set on Destination)      |
   +------------------+-----------+----------------------+-----------------------------------+
   | Title            |     <-    | ID                   | New                               |
   +------------------+-----------+----------------------+-----------------------------------+
   | Version/Label    |     <-    | Sprint/Version       | Sync                              |
   +------------------+-----------+----------------------+-----------------------------------+

2. Attributes mapping on trackers:

   +------------------+------------------+------------------+------------------+------------------+
   | Name             | Github           | Gitlab           | JIRA             | RTC              |
   +==================+==================+==================+==================+==================+
   | Title            | Title            | Title            | Title            | Title            |
   +------------------+------------------+------------------+------------------+------------------+
   | URL              | URL              | URL              | URL              | URL              |
   +------------------+------------------+------------------+------------------+------------------+
   | Assignee         | Assignee         | Assignee         | Assignee         | Owner            |
   +------------------+------------------+------------------+------------------+------------------+
   | Component        | Repository       | Repository       | Component        | Component        |
   +------------------+------------------+------------------+------------------+------------------+
   | Status           | Status           | Status           | Status           | Status           |
   +------------------+------------------+------------------+------------------+------------------+
   | Story point      | Labels (x pts)   | Labels (x pts)   | Estimate         | Story point      |
   +------------------+------------------+------------------+------------------+------------------+
   | Priority         | Labels (prio x)  | Labels (prio x)  | Priority         | Priority         |
   +------------------+------------------+------------------+------------------+------------------+
   | Sprint           | Labels           | Labels           | Labels           | Planned For      |
   +------------------+------------------+------------------+------------------+------------------+

3. JSON configuration file

- Tracker configuration:

  + Github:

    * Project
    * Token
    * Repository
    * Allow condition

  + Gitlab
  + JIRA
  + RTC

- User configuration