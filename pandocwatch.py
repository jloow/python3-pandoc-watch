#!/usr/bin/env python3
"""Watch a directory for updates and run pandoc when it changes.
"""

import os
import sys
import subprocess
import datetime
import time
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def which(program):
    """Locates a program in the user's $PATH.

    This function is taken from
    http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python

    Args:
        program: The program we wish to find.

    Returns:
        Path to the executable or None if not found.
    """
    is_exe = lambda fpath: os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


class Singleton(type):
    """ Dead-simple singleton metaclass.

    Taken from:
    http://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args,
                                                                 **kwargs)
        return cls._instances[cls]


class Configuration(metaclass=Singleton):
    """ Configuration for pandocwatch. """

    def __init__(self):
        self.command = ""
        self.dir_content_and_time = ""
        self.excluded_file_extensions = []
        self.excluded_folders = []

    def watched_elements(self):
        """ Get a list of elements that we are watching. """
        elements = []
        for path in os.listdir(os.getcwd()):
            path_to_remove = False
            for extension in self.excluded_file_extensions:
                if path.endswith(extension):
                    path_to_remove = True
                    break
            if not path_to_remove and not path in self.excluded_folders:
                elements.append((path, os.stat(path).st_mtime))
        return elements


def recompile():
    """Run pandoc, printing the program's output.

    Writes the error to STDOUT if present.
    """
    config = Configuration()
    print("Updating the output at {}"
          .format(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")),
          file=sys.stderr)
    print("executing command : {}".format(config.command))
    os.chdir(os.path.abspath(os.getcwd()))
    try:
        subprocess.check_output(
            config.command,
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True
        )
        print("No error found")
    except subprocess.CalledProcessError as err:
        print("Error:\n{}".format(err.output))


class ChangeHandler(FileSystemEventHandler):
    """Handler for watching a folder for changes and running pandoc."""

    def on_modified(self, event):
        config = Configuration()
        local_dir_content = config.watched_elements()
        found = False
        for (path, m_time) in local_dir_content:
            for (bpath, bm_time) in config.dir_content_and_time:
                if path == bpath:
                    if m_time > bm_time:
                        print("File {} has changed. Recompiling.".format(path))
                        found = True
                        config.dir_content_and_time = local_dir_content
                        recompile()
                        print("Recompilation done")
                        break
            if found:
                break


def build_args():
    """ Build the CLI options.

    Returns:
        argparse.ArgumentParser for pandocwatch's arguments.
    """
    pandoc_output = subprocess.check_output(["pandoc", "--help"],
                                            universal_newlines=True)
    added_epilog = '\n'.join(str(pandoc_output).split("\n")[1:])
    epilog = ("-------------------------------------------\n"
              "Pandoc standard options are: \n\n{}"
              .format(added_epilog))
    parser = argparse.ArgumentParser(
        description="Watcher for pandoc compilation",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-e", "--exclude",
                        dest="exclusions",
                        default=".pdf,.tex,doc,bin,common",
                        required=False,
                        help="The extensions (.pdf for pdf files) "
                        "or the folders to exclude from watch "
                        "operationsr, separated by commas")
    return parser


def setup_config(args_parser):
    """Set the configuration settings in accordance with the CLI args.
    """
    args = args_parser.parse_known_args()
    exclusions = args[0].exclusions
    exclusions = exclusions.split(",")
    config = Configuration()

    config.excluded_file_extensions = (
        [value for value in exclusions if value.startswith(".")])
    config.excluded_folders = (
        list(set(exclusions)
             .symmetric_difference(set(config.excluded_file_extensions))))

    pandoc_options = ' '.join(args[1])

    if not pandoc_options:
        print("pandoc options must be provided!\n")
        args_parser.print_help()
        exit()

    config.command = "pandoc " + pandoc_options


def main(): #pylint: disable=missing-docstring
    pandoc_path = which("pandoc")
    if not pandoc_path:
        print("pandoc executable must be in the path!", file=sys.stderr)
        exit()

    config = Configuration()
    setup_config(build_args())
    config.dir_content_and_time = config.watched_elements()

    print("Starting pandoc watcher ...")
    while True:
        event_handler = ChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, os.getcwd(), recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt as err:
            print(str(err))
            observer.stop()

        print("Stopping pandoc watcher ...")
        exit()

if __name__ == '__main__':
    main()
