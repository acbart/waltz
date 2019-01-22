# waltz
A software system for synchronizing LMS course content with repositories, for computing courses.

# Architecture

There are two pieces of software here

* Waltz API: An API for syncing the LMS course content and the repo
* WaltzWeb: A web interface for managing content between the sources.

# Waltz API

Largely makes calls to Canvas to pull and push content.

# Waltz Web

Largely client-side interfaces for negotiating the changes. Makes calls to commit stuff to GitHub.

# Terminology

* Resource: A thing to be pushed or pulled to Canvas. Some resources can be composed of other resources.
* Name: Names are important - they are how things get synched. You can use the Name Changer tool to relabel things.

# Interfaces

Sync content between different LMS resources

* TextContent: 
    * A string of data that can be converted into HTML or parsed back into Markdown
    * Can be associated with a Template to structure the conversion process

* Page: Basically just a TextContent
* Quiz: 
* Exercise/Project/Lab: Basically just a TextContent and a hyperlink
* File: 
* Rubric:
* Learning Outcomes:

# Page Templates

* Syllabus:
* Course Staff Information:
* Lesson:
* Module:
* Reference:
* Exam Prep:
* Style Guide:
* Content:
* Worked Example:
* Video:
* Slides:

# Public/Private Mirrors

Many courses have resources (typically quizzes, programming exercises, etc.) that must be kept private. Waltz supports the creation of Public mirrors of the primary (private) course repository, intelligently stripping away information that needs to be kept private. Trusted users can be given access to the primary repo, while untrusted users can still be given partial access through the public mirror.

Workflow:

1. Fetch the latest Private repo's contents to the Public repo
2. Strip away any files described in the private repo's .gitignore
    git filter-branch --tree-filter 'rm *.csv *.zip' HEAD
3. Merge