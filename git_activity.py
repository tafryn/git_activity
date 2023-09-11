#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Git activity display tool

This module displays the git active days (gads) for several git repositories
and several authors. The authors, repositories, and duration are configured in
a separate configuration file. An author's gads are colored differently for
each repository, and also for days when there were commits to multiple
repositories.

The number of repositories is limited by the length of the COLORWAYS list.

TODO:
    * Reinsert column headings at screen height marks
    * Use number in legend of numeric mode

"""

import sys
import os
import datetime
import calendar
import argparse
import re
from itertools import groupby, chain, izip
from pyparsing import Literal, Word, Combine, Optional, oneOf, Suppress, nums, delimitedList, alphas
import yaml
import git
from terminaltables import AsciiTable, SingleTable, DoubleTable
from colored import fg, attr

TODAY = datetime.date.today()

DUMMY_GAD = (TODAY, {'~/path_one': 0, '~/path_two': 1, '~/path_three': 2})

COLORWAYS = [
    [236, 94, 136, 172, 208],   # oranges
    [236, 58, 100, 142, 184],   # yellows
    [236, 22, 28, 34, 40],      # greens
    [236, 23, 30, 37, 44],      # cyans
    [236, 53, 90, 127, 164],    # purples
    [236, 17, 18, 19, 20],      # blues
    [236, 52, 88, 124, 160],    # reds
    [236, 238, 241, 248, 255],  # grays
]

DEFAULT_COLOR = 244

MAX_HEIGHT = int(os.popen('stty size', 'r').read().split()[0])
MAX_WIDTH = int(os.popen('stty size', 'r').read().split()[1])


def id(x):
    return x


def non_ansi_len(input_string):
    """Calculate the length of input_string without ansi escape codes."""
    esc = Literal('\x1b')
    integer = Word(nums)
    escape_seq = Combine(esc + '[' + Optional(delimitedList(integer, ';')) + oneOf(list(alphas)))
    non_ansi_string = lambda s: Suppress(escape_seq).transformString(s)
    uncolor_string = non_ansi_string(input_string)
    return len(uncolor_string)


def only1(iterable):
    """Return true if only one of the elements of iterable is true and false
       otherwise.
    """
    i = iter(iterable)
    return any(i) and not any(i)


def split_list_on(element, lst):
    """The equivalent of split for generic lists

    There has to be a better way to do this.
    """
    split_lists = []
    temp_list = []
    for i in xrange(0, len(lst)):
        if lst[i] == element:
            split_lists.append(temp_list)
            temp_list = []
        else:
            temp_list.append(lst[i])

    return split_lists


def diagonally_reflect(lst):
    """Reflect the supplied two dimensional list over the diagonal."""
    return [[list(column) for column in zip(*row)] for row in lst]


def month_dates(year, month):
    """Return a list of weeks which are, in turn, lists of days."""
    return calendar.TextCalendar(calendar.SUNDAY).monthdatescalendar(year, month)


def previous_month(date):
    """Return the last day of the month prior to date."""
    return date.replace(day=1) - datetime.timedelta(days=1)


def join_date_months(preceding_month, current_month):
    """Join two lists of weeks of adjoining months."""
    if current_month[0][0].month == current_month[0][-1].month:
        return preceding_month + current_month

    return preceding_month[:-1] + current_month


def last_n_weeks(date, num_weeks=1):
    """Return a list of the n weeks prior to date."""
    starting_month = month_dates(date.year, date.month)

    for i, week in enumerate(starting_month):
        if date in week:
            starting_month = starting_month[:i+1]
            break

    current_weeks = starting_month
    current_date = date

    while len(current_weeks) < num_weeks:
        current_date = previous_month(current_date)
        earlier_month_dates = month_dates(current_date.year, current_date.month)
        current_weeks = join_date_months(earlier_month_dates, current_weeks)

    return current_weeks[len(current_weeks)-num_weeks:]


def count_commits_for(repository_dir, num_weeks, author=""):
    """Tally up the commits to a git repository for the last num_weeks.

    Optionally, only count commits for the specified author.
    """
    repo_cmd = git.Git(os.path.expanduser(repository_dir))
    log_options = [
        '--all',
        '--pretty=format:"%at"',
        '--use-mailmap',
        "--since=\"%d weeks\"" % num_weeks]
    if author != "":
        log_options.append("--author=%s" % author)
    commit_stamp_strings = repo_cmd.log(*log_options).split('\n')
    commits_counted_by_date = {}
    if commit_stamp_strings != [""]:
        commit_dates = [datetime.date.fromtimestamp(int(x.replace('"', '')))
                        for x in commit_stamp_strings]
        for commit_date in [list(date_group[1]) for date_group in groupby(commit_dates, id)]:
            commits_counted_by_date[commit_date[0]] = len(commit_date)

    return commits_counted_by_date


def fetch_commits(repository_dirs, verbose):
    """Fetch any available commits for the supplied list of repositories."""
    for repository_dir in repository_dirs:
        git_repo = git.Repo(os.path.expanduser(repository_dir),
                            search_parent_directories=True)
        for remote in git_repo.remotes:
            if verbose >= 1:
                print("Fetching commits for "
                      + os.path.basename(git_repo.working_dir)
                      + ":" + remote.name).encode('utf-8')
            remote.fetch()


def auto_detect_top_authors(repositories, since, quantity):
    """Automatically detect the top five contributors for each repository."""
    auto_detected_authors = []
    for repo in repositories:
        git_cmd = git.Git(os.path.expanduser(repo))
        log_options = ['-s', '-n', '--all', '--since', since]
        raw_authors = git_cmd.shortlog(*log_options).split('\n')[:int(quantity)]
        for raw_author in raw_authors:
            auto_detected_authors += [re.sub(r'^.*\t', '', raw_author)]

    if u'' in auto_detected_authors:
        auto_detected_authors.remove(u'')
    return auto_detected_authors


def generate_legend(repositories, gads):
    """Generate a legend for the provided list of repositories."""
    legend = []
    active_repos = active_repositories(repositories, gads)
    for index, value in enumerate({repo: 0 for repo in repositories}.keys()):
        if value in active_repos:
            legend.append(render_colored_block_string(COLORWAYS[index % (len(COLORWAYS) - 1)][4])[0][0] + " " +
                        colorize_string(os.path.basename(value.rstrip('/')), DEFAULT_COLOR))

    legend.append(render_colored_block_string(COLORWAYS[-1][4])[0][0] + " " +
                  colorize_string("multiple", DEFAULT_COLOR))
    return "\n".join(legend)


def determine_color_for(gad, quartiles):
    """Return the appropriate color for the total number of commits on gad.

    The hue of the color is determined by the repository. The intensity of the
    color depends on where the number of commits on gad falls with respect to
    the provided quartiles.
    """
    repo_color_key = list(gad[1].keys())
    active_repo = ""
    colorway = 0
    color_index = 0
    total_commits = 0

    for repo_name, commit_count in gad[1].iteritems():
        if commit_count > 0:
            active_repo = repo_name
            total_commits += commit_count

    if not only1(gad[1].values()):
        colorway = len(COLORWAYS) - 1
    else:
        colorway = repo_color_key.index(active_repo) % (len(COLORWAYS) - 1)

    if total_commits == 0:
        color_index = 0
    elif total_commits <= quartiles[0]:
        color_index = 1
    elif total_commits <= quartiles[1]:
        color_index = 2
    elif total_commits <= quartiles[2]:
        color_index = 3
    else:
        color_index = 4

    return COLORWAYS[colorway][color_index]


def colorize_string(string, color, default=DEFAULT_COLOR):
    """Add color codes to the provided string"""
    return fg(color) + string + fg(default)


def render_numeric_string(number, color=1):
    """Return a numeric string represeting the totoal number of commits on gad.
    """
    if number > 99:
        rendered_string = "**"
    elif number > 0:
        rendered_string = "%2d" % number
    else:
        rendered_string = "--"

    return [[colorize_string(rendered_string, color)]]


def render_colored_block_string(color=1, emphasize=False):
    """Return a colored block.

    Optionally return an emphasized block instead.
    """
    block = u"\u25fc"
    em_blocks = [u"\u25cf", u"\u25c6", u"\u25a2"]
    if emphasize:
        return [[colorize_string(em_blocks[0], color)]]

    return [[colorize_string(block, color)]]


def render_numeric_gad(gad, quartiles):
    """Return a numeric string representing the gad."""
    return render_numeric_string(sum(gad[1].values()), determine_color_for(gad, quartiles))


def render_colored_block_gad(gad, quartiles):
    """Return a colored block representing the gad."""
    return render_colored_block_string(determine_color_for(gad, quartiles))


def render_gads(gad_weeks, gad_render_func, quartiles=(1, 3, 5)):
    """Return a multiline string representing the gads in gad_weeks."""
    rendered_string_list = []
    element_width = non_ansi_len(gad_render_func(DUMMY_GAD, quartiles)[0][0])
    for week in gad_weeks:
        if week[0][0].year != week[6][0].year or week[0][0].day == 1 and week[0][0].month == 1:
            rendered_string_list += [[char] for char in "%s    " % week[6][0].strftime("%Y")]
            rendered_string_list.append(["\n"])
        for gad in week:
            rendered_string_list += gad_render_func(gad, quartiles)
        if week[0][0].month != week[6][0].month or week[0][0].day == 1:
            rendered_string_list.append([week[6][0].strftime("%b")])
        else:
            rendered_string_list.append([" " * element_width])
        rendered_string_list.append(["\n"])

    return rendered_string_list


def render_author(author_string, gad_counts, display_mode, show_total):
    """Return a name string with an optional total determined by the display_mode."""
    width_limit = MAX_WIDTH - 5
    trailing_text = ""
    if show_total:
        if display_mode == "block":
            trailing_text = str(len(gad_counts))
        elif display_mode == "numeric":
            trailing_text = str(sum(gad_counts))

    if len(author_string + trailing_text) > width_limit:
        author_string = author_string[:width_limit - len(trailing_text)]

    return colorize_string(author_string + " " + colorize_string(trailing_text, DEFAULT_COLOR), 255)


def render_author_gads(author_gads, gads_render_func, author_render_func, orientation):
    """Return a pair of lists of rendered authors and gads."""
    authors = []
    rendered_gads = []

    for author, gads in author_gads.iteritems():
        authors.append(author_render_func(author, daily_commit_counts(gads)))
        rendered_gads.append(gads_render_func(gads, calculate_quartiles(daily_commit_counts(gads))))

    split_rendered_gads = [split_list_on(['\n'], l) for l in rendered_gads]

    if orientation == "vertical":
        unboxed_gads = merge_rendered_gads(split_rendered_gads)
    elif orientation == "horizontal":
        unboxed_gads = merge_rendered_gads(diagonally_reflect(split_rendered_gads))
        unboxed_gads = [adjust_month_label_spacing(gad_month) for gad_month in unboxed_gads]
    else:
        exit(1)

    return (authors, unboxed_gads)


def display_tabled_gads(authors, rendered_gad_months, title, border, width=0):
    """Display a table of gads per author according to gads_render_func."""
    if len(authors) <= 1:
        width = 1
    elif width == 0:
        gad_width = max([non_ansi_len(l) for l in rendered_gad_months[1].splitlines()])
        author_width = max([non_ansi_len(a) for a in authors])
        auto_width = (MAX_WIDTH - 1) / (max(gad_width, author_width) + 3)
        width = max(1, auto_width)

    table_data = list(chain.from_iterable(izip(
        [authors[i:i + width] for i in xrange(0, len(authors), width)],
        [rendered_gad_months[i:i + width] for i in xrange(0, len(rendered_gad_months), width)])))

    if border == "ascii":
        display_table = AsciiTable(table_data)
    elif border == "single":
        display_table = SingleTable(table_data)
    elif border == "double":
        display_table = DoubleTable(table_data)
    else:
        exit(1)

    display_table.inner_row_border = True
    display_table.inner_column_border = True
    display_table.title = title

    sys.stdout.write(fg(DEFAULT_COLOR))
    print display_table.table.encode('utf-8'), attr(0).encode('utf-8')


def merge_rendered_gads(rendered_gads):
    """Merge the 2d list of rendered gads into a single string."""
    return ["\n".join(
        [" ".join(
            [char for box in week for char in box])
         for week in gads])
            for gads in rendered_gads]


def adjust_month_label_spacing(gad_month_string):
    """Correct the spacing for the month labels in horizontally rendered gad_months.

    This works for now, but represents a substantial technical debt.
    """
    first_re = re.compile(r"^((.*\n)+)(.*)$", re.MULTILINE)
    first_match = first_re.match(gad_month_string)
    element_width = non_ansi_len(first_match.groups()[1].split(" ")[0])
    overrun = 3 - element_width  # 3 is the width of the month labels
    month_line = re.findall(r"\s+|\w+", first_match.groups()[2])
    mod_month_line = month_line[:1] \
        + [x[:-overrun] if re.match(r"\s+", x) else x for x in month_line[1:]]
    mod_month_line = ["  " if len(x) < element_width else x for x in mod_month_line]
    return first_match.groups()[0] + "".join(mod_month_line)


def daily_commit_counts(gads):
    """Flatten a list of gads by week and return a list of total commits on each day."""
    flat_gads = [day for week in gads for day in week]
    total_commits_per_day = [sum(x[1].values()) for x in flat_gads]
    return [commits for commits in total_commits_per_day if commits != 0]


def active_repositories(repositories, gads):
    """Return the subset of repositories that have commits in gads."""
    total_activity = {}
    for repo in repositories:
        total_activity[repo] = 0
    for weeks in gads.values():
        flat_activity = [day[1] for week in weeks for day in week]
        for repo_activity in flat_activity:
            for repo in repositories:
                total_activity[repo] += repo_activity[repo]
    return [x for x in total_activity.keys() if total_activity[x] > 0]


def calculate_quartiles(list_of_numbers):
    """Returns the 1st, 2nd, and 3rd quartile of a list of ints as a tuple."""
    if list_of_numbers:
        list_of_numbers.sort()
        quartile_1 = list_of_numbers[int(len(list_of_numbers) / 4)]
        quartile_2 = list_of_numbers[int(len(list_of_numbers) / 2)]
        quartile_3 = list_of_numbers[3 * int(len(list_of_numbers) / 4)]
        return (quartile_1, quartile_2, quartile_3)

    return (0, 0, 0)


def gad_zip(annotated_date, sum_commits, repo_dir):
    """Populate an annotated date with the number of commits for repo_dir."""
    count = 0
    if annotated_date[0] in sum_commits.keys():
        count = sum_commits[annotated_date[0]]

    annotated_date[1][repo_dir] = count
    return annotated_date


def aggregate_gads(repositories, time_period, authors):
    """Calculate the gads for each author on each repository during the supplied time_period."""
    if authors:
        gads_by_author = {}
        for author in authors:
            gads_by_date = [[(day, {}) for day in week] for week in time_period]
            for repo_dir in repositories:
                counted_commits = count_commits_for(repo_dir, len(time_period), author)
                gads_by_date = [[gad_zip(day, counted_commits, repo_dir) for day in week]
                                for week in gads_by_date]
            gads_by_author[author] = gads_by_date[:]

        return gads_by_author

    gads_per_repo = {}
    for repo_dir in repositories:
        gads_by_date = [[(day, {}) for day in week] for week in time_period]
        counted_commits = count_commits_for(repo_dir, len(time_period))
        gads_by_date = [[gad_zip(day, counted_commits, repo_dir) for day in week]
                        for week in gads_by_date]
        gads_per_repo[repo_dir] = gads_by_date[:]

    return gads_per_repo


def exception_handler(exception_type, exception, traceback, verbose, debug_hook=sys.excepthook):
    """Exception handler to suppress traceback in production."""
    if verbose:
        debug_hook(exception_type, exception, traceback)
    else:
        print("%s: %s" % (exception_type.__name__, exception)).encode('utf-8')


def positive_int(value):
    """Argparse handler for positive int types."""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue


def main():
    """Main method"""
    arg_parser = argparse.ArgumentParser(
        description='Display commit activity by author for several repositories.')
    arg_parser.add_argument('-A', '--auto_detect',
                            help='automatically detect five authors per repo',
                            type=positive_int,
                            nargs='?',
                            const=5)
    arg_parser.add_argument('-b', '--border',
                            help='format of the table borders',
                            choices=['ascii', 'single', 'double'],
                            default="ascii")
    arg_parser.add_argument('-c', '--clear',
                            help='clear the screen prior to gad display',
                            action='store_true')
    arg_parser.add_argument('-d', '--duration',
                            help='time period in weeks',
                            type=positive_int,
                            default=12)
    arg_parser.add_argument('-D', '--display_type',
                            help='format of the gad display',
                            choices=['numeric', 'block'],
                            default="block")
    arg_parser.add_argument('-E', '--exceptions',
                            help='display full exception text',
                            action='store_true')
    arg_parser.add_argument('-F', '--fetch',
                            help='fetch new upstream commits for the configured repositories',
                            action='store_true')
    arg_parser.add_argument('-f', '--file',
                            help='read configuration from FILE')
    arg_parser.add_argument('-l', '--legend',
                            help='display a legend as the last entry in the table',
                            action='store_true')
    arg_parser.add_argument('-o', '--orientation',
                            help='orientation of the displayed gads',
                            choices=['vertical', 'horizontal'],
                            default="vertical")
    arg_parser.add_argument('-t', '--total',
                            help='display a summary total adjacent to the author\'s name',
                            action='store_true')
    arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s 0.9')
    arg_parser.add_argument('-v', '--verbose',
                            help='set the verbosity level (multiple allowed)',
                            action='count')
    arg_parser.add_argument('-w', '--width',
                            help='display WIDTH columns',
                            type=positive_int,
                            default=0)
    args = arg_parser.parse_args()

    sys.excepthook = lambda et, e, tb: exception_handler(et, e, tb, args.exceptions)

    # Default values for configuration file options
    authors = []
    repositories = ["./"]

    config_file = args.file if args.file is not None else "~/.config/git_activity.yml"

    if os.path.exists(os.path.expanduser(config_file)):
        with open(os.path.expanduser(config_file), "r") as yml_file:
            cfg = yaml.load(yml_file)

            if cfg:
                if 'repositories' in cfg and cfg['repositories']:
                    repositories = cfg['repositories']

                if 'authors' in cfg and cfg['authors']:
                    authors = cfg['authors']

    time_period = last_n_weeks(TODAY, args.duration)

    if args.fetch:
        fetch_commits(repositories, args.verbose)

    if args.auto_detect:
        authors += auto_detect_top_authors(repositories,
                                           time_period[0][0].strftime("%m-%d-%y"),
                                           args.auto_detect)

    # Remove duplicates from the list of authors
    authors = list(set(authors))

    gads_by_author = aggregate_gads(repositories, time_period, authors)

    if args.display_type == "block":
        gad_render_func = lambda g, q: render_gads(g, render_colored_block_gad, q)
        author_render_func = lambda a, gc: render_author(a, gc, args.display_type, args.total)
    elif args.display_type == "numeric":
        gad_render_func = lambda g, q: render_gads(g, render_numeric_gad, q)
        author_render_func = lambda a, gc: render_author(a, gc, args.display_type, args.total)
    else:
        arg_parser.error("Unknown display type: %s" % args.display_type)

    authors, rendered_gad_months = render_author_gads(gads_by_author,
                                                      gad_render_func,
                                                      author_render_func,
                                                      args.orientation)

    if args.legend:
        authors.append(colorize_string("Legend", 255))
        rendered_gad_months.append(generate_legend(repositories, gads_by_author))

    time_period_label = str(time_period[0][0]) + " to " + str(time_period[-1][-1])

    if args.clear:
        print "\033c",

    display_tabled_gads(authors,
                        rendered_gad_months,
                        colorize_string(time_period_label, 255),
                        args.border,
                        args.width)


if __name__ == "__main__":
    main()
