# Git Activity

This module displays commit activity for git repositories in tabular form. By
default activity is displayed for the whole repository, but activity can be
displayed per author as well. There are two display modes: block and numeric.
The first displays colored blocks, and the latter displays the number of
commits, on active days.

### Supported Options

```
usage: git_activity.py [-h] [-A [AUTO_DETECT]] [-b {ascii,single,double}]
                       [-d DURATION] [-D {numeric,block}] [-E] [-F] [-f FILE]
                       [-l] [-o {vertical,horizontal}] [-t] [-v] [-w WIDTH]

Display commit activity by author for several repositories.

optional arguments:
  -h, --help            show this help message and exit
  -A [AUTO_DETECT], --auto_detect [AUTO_DETECT]
                        automatically detect five authors per repo
  -b {ascii,single,double}, --border {ascii,single,double}
                        format of the table borders
  -c, --clear           clear the screen prior to gad display
  -d DURATION, --duration DURATION
                        time period in weeks
  -D {numeric,block}, --display_type {numeric,block}
                        format of the gad display
  -E, --exceptions      display full exception text
  -F, --fetch           fetch new upstream commits for the configured
                        repositories
  -f FILE, --file FILE  read configuration from FILE
  -l, --legend          display a legend as the last entry in the table
  -o {vertical,horizontal}, --orientation {vertical,horizontal}
                        orientation of the displayed gads
  -t, --total           display a summary total adjacent to the author's name
  -V, --version         show program's version number and exit
  -v, --verbose         set the verbosity level (multiple allowed)
  -w WIDTH, --width WIDTH
                        display WIDTH columns
```

### Prerequisites

The module expects to be run in a terminal that supports 256 colors and unicode
characters.

### Installing

A setup script is provided to install the module and its dependencies.
```
$ python setup.py build
$ python setup.py install --user
```

### Example

```
$ git_activity.py -d 52 -o horizontal -A -b single
```

### Config File

The module looks for a configuration file in the user's home directory under
.config/git\_activity.yml. It expects this to be a yaml file with two lists,
`repositories` and, optionally, `authors`.

Example config file
```
repositories:
    - /home/user/repository_one
    - ~/repository_two
    - repository_three

authors:
    - John Smith
    - janes
    - tom.smith@example.invalid
```
