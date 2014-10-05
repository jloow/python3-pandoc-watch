#!/usr/bin/env python3

import os
import sys
import subprocess
import datetime
import time
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def which(program):
    """
    This function is taken from http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    """
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
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
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Configuration(metaclass=Singleton):

    def __init__(self):
        print('inside {}'.format(self))
        self._command = ""
        self._dirContentAndTime = ""
        self._excludedFileExtensions = []
        self._excludedFolders = []

    def setCommand(self, command):
        self._command = command

    def getCommand(self):
        return self._command

    def setExcludedFileExtensions(self, excluded_file_extensions):
        self._excludedFileExtensions = excluded_file_extensions

    def getExcludedFileExtensions(self):
        return self._excludedFileExtensions

    def setDirContentAndTime(self, dir_content_and_time):
        self._dirContentAndTime = dir_content_and_time

    def getDirContentAndTime(self):
        return self._dirContentAndTime

    def setExcludedFolders(self,excluded_folders):
        self._excludedFolders = excluded_folders

    def getExcludedFolders(self):
        return self._excludedFolders

def getext(filename):
    "Get the file extension."

    return os.path.splitext(filename)[-1].lower()

def get_now():
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

def getDirectoryWatchedElements():
    config = Configuration()
    elements = []
    for path in os.listdir(os.getcwd()):
        path_to_remove = False
        for extension in config.getExcludedFileExtensions():
            if path.endswith(extension):
                path_to_remove = True
                break
        if not path_to_remove and not path in config.getExcludedFolders():
            elements.append((path,os.stat(path).st_mtime))
    return elements

def recompile():
    config = Configuration()
    print("Updating the output at %s" % get_now(), file=sys.stderr)
    print("executing command : {}".format(config.getCommand()))
    os.chdir(os.path.abspath(os.getcwd()))
    try:
        output = subprocess.check_output(
            config.getCommand(),
            stderr=subprocess.STDOUT,
            shell=True,
            universal_newlines=True
        )
        print("No error found")
    except subprocess.CalledProcessError as err:
        print("Error:\n{}".format(err.output))

class ChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        config = Configuration()
        local_dir_content = getDirectoryWatchedElements()
        found = False
        for (path, m_time) in local_dir_content:
            for (bpath,bm_time) in config.getDirContentAndTime() :
                if path == bpath :
                    if m_time > bm_time :
                        print("File {} has changed. Recompiling.".format(path))
                        found = True

                        config.setDirContentAndTime(local_dir_content)
                        recompile()
                        print("Recompilation done")
                        break
            if found :
                break

def parse_options():
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
    args = parser.parse_known_args()

    exclusions = args[0].exclusions
    exclusions = exclusions.split(",")

    config = Configuration()

    config.setExcludedFileExtensions(
        [value for value in exclusions if value.startswith(".")])
    config.setExcludedFolders(
        list(set(exclusions).symmetric_difference(set(config.getExcludedFileExtensions()))))

    pandoc_options = ' '.join(args[1])

    if not pandoc_options :
        print("pandoc options must be provided!\n")
        parser.print_help()
        exit()

    config.setCommand("pandoc " + pandoc_options)

def main():

    pandoc_path = which("pandoc")
    if not pandoc_path :
        print("pandoc executable must be in the path to be used by pandoc-watch!")
        exit()

    config = Configuration()

    parse_options()

    config.setDirContentAndTime(getDirectoryWatchedElements())

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
