# waltz

A software system for synchronizing curricular materials between a
Learning Management Systems (LMS) and your local filesystem.

Currently, we have support for the following LMS:
* Canvas (pages, assignments, quizzes)
* BlockPy (assignment, groups) <- In-progress

# Installation

You can install Waltz from PyPi (the package name is `lms-waltz` even though the module and command line script is `waltz`):

```console
$> pip install lms-waltz
```

You can also install our dev version from GitHub:

```console
$> pip install git+https://github.com/acbart/waltz.git
```

## Setup Waltz

Waltz can synchronize content between a local directory and a remote server.
You'll need to initialize the local directory, whether it is empty or already has your learning materials.

```console
$> waltz init
```

This will create two new files which should both be included in your `.gitignore`:

* `.waltz` is a plain-text YAML file with settings for the current course repository.
* `.waltz.db` is a SQLite database used in file uploading/downloading.

## Setup a Service

Before you can start interacting with an LMS, you'll need to configure an
instance of a service. For example, to configure a new Canvas service, you'll need the following:

1. A short, easy-to-type name for the service instance (e.g., `ud_canvas` or `cs1014_canvas`)
2. [API token](https://community.canvaslms.com/docs/DOC-10806-4214724194)
3. The URL base for your Canvas site (e.g., `https://canvas.instructure.com/`)
4. The Course ID that you want to connect to (usually a large number)

Then, you can use the command below:

```console
$> waltz configure canvas <name> --base <url> --course <id> --token <token>
```

A more concrete example:

```console
$> waltz configure canvas ud_canvas --base https://udel.instructure.com/ --course 4234343432343 --token 1081~zJIOJSDFBBSDFIJAIJ==>...
```

If things went well, you can list the available services:

```console
$> waltz list
The following services are available:
         local:
                 ./
         canvas:
                 ud_canvas
         blockpy: (none configured)
```

By default, there's a Local service for the current directory (representing the connection to the filesystem).
You can have more than one instance of a service, which can allow you to
access multiple data sources from one course (e.g., to transfer resources between semesters).
For convenience, you can refer to the first instance of a service by the service's name.
In our case, anywhere that we use `ud_canvas` we could use `canvas` instead.

## Managing Resources

You can list available resources for a service:

```console
$> waltz canvas list pages
```

Similar to Git, you can use `waltz` commands from child folders and the system will search up for the configuration.

If the desired files are not in the present folder, it will search subfolders.

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

# Full Command Reference

> waltz reset

> waltz