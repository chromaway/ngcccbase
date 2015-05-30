#!/usr/bin/env python


import apigen
from ngcccbase.api import Ngccc
import threading

import sys
import linecache
line_count = 0




def traceit(frame, event, arg):
    global line_count

    if event == 'call':
        co = frame.f_code
        func_name = co.co_name
        func_line_no = frame.f_lineno
        func_filename = co.co_filename
        caller = frame.f_back
        caller_line_no = caller.f_lineno
        caller_filename = caller.f_code.co_filename
        name = frame.f_globals["__name__"]
        if 'ngccc' in name or 'apigen' in name:
            line_count += 1

            # print 'Call to %s on line %s of %s from line %s of %s\n' % (func_name, func_line_no, func_filename, caller_line_no, caller_filename)
            print "%s def %s" % (line_count, func_name)
        return traceit    # if event == 'return':
    #     print "return is %s" % event

    if event in ("return", "line"):
        lineno = frame.f_lineno
        name = frame.f_globals["__name__"]
        filename = None
        if 'ngccc' in name or 'apigen' in name:
            try:
                filename = frame.f_globals["__file__"]
            except KeyError:
                print "no file name"
                return traceit
            if filename:
                if (filename.endswith(".pyc") or
                    filename.endswith(".pyo")):
                    filename = filename[:-1]
                line = linecache.getline(filename, lineno)
            else:
                line = "no line"
            line_count += 1
            print "%s - %s:%s: %s" % (line_count, name, lineno, line.rstrip())

    return traceit

# threading.settrace(traceit)
# sys.settrace(traceit)

if __name__ == "__main__":
    apigen.run(Ngccc)

