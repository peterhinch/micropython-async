#! /usr/bin/python3
# -*- coding: utf-8 -*-
# check_async_code.py
# A simple script to identify a common error which causes silent failures under
# MicroPython (issue #3241).
# This is where a task is declared with async def and then called as if it were
# a regular function.
# Copyright Peter Hinch 2017
# Issued under the MIT licence

import sys
import re

tasks = set()
mismatch = False

def pass1(part, lnum):
    global mismatch
    opart = part
    sysnames = ('__aenter__', '__aexit__', '__aiter__', '__anext__')
    # These are the commonest system functions declared with async def.
    # Mimimise spurious duplicate function definition error messages.
    good = True
    if not part.startswith('#'):
        mismatch = False
        part = stripquotes(part, lnum)  # Remove quoted strings (which might contain code)
        good &= not mismatch
        if part.startswith('async'):
            pos = part.find('def')
            if pos >= 0:
                part = part[pos + 3:]
                part = part.lstrip()
                pos = part.find('(')
                if pos >= 0:
                    fname = part[:pos].strip()
                    if fname in tasks and fname not in sysnames:
                        # Note this gives a false positive if a method of the same name
                        # exists in more than one class.
                        print('Duplicate function declaration "{}" in line {}'.format(fname, lnum))
                        print(opart)
                        print()
                        good = False
                    else:
                        tasks.add(fname)
    return good

# Strip quoted strings (which may contain code)
def stripquotes(part, lnum=0):
    global mismatch
    for qchar in ('"', "'"):
        pos = part.find(qchar)
        if pos >= 0:
            part = part[:pos] + part[pos + 1:]  # strip 1st qchar
            pos1 = part.find(qchar)
            if pos > 0:
                part = part[:pos] + part[pos1+1:]  # Strip whole quoted string
                part = stripquotes(part, lnum)
            else:
                print('Mismatched quotes in line', lnum)
                mismatch = True
                return part  # for what it's worth
    return part

def pass2(part, lnum):
    global mismatch
    opart = part
    good = True
    if not part.startswith('#') and not part.startswith('async'):
        mismatch = False
        part = stripquotes(part, lnum)  # Remove quoted strings (which might contain code)
        good &= not mismatch
        for task in tasks:
            sstr = ''.join((task, r'\w*'))
            match = re.search(sstr, part)
            if match is None:  # No match
                continue
            if match.group(0) != task:  # No exact match
                continue
            # Accept await task, await task(args), a = await task(args)
            sstr = ''.join((r'.*await[ \t]+', task))
            if re.search(sstr, part):
                continue
            # Accept await obj.task, await obj.task(args), a = await obj.task(args)
            sstr = ''.join((r'.*await[ \t]+\w+\.', task))
            if re.search(sstr, part):
                continue
            # Accept assignments e.g. a = mytask or
            # after = asyncio.after if p_version else asyncio.sleep
            # or comparisons thistask == thattask
            sstr = ''.join((r'=[ \t]*', task, r'[ \t]*[^(]'))
            if re.search(sstr, part):
                continue
            # Not awaited but could be passed to function e.g.
            # run_until_complete(mytask(args))
            sstr = ''.join((r'.*\w+[ \t]*\([ \t]*', task, r'[ \t]*\('))
            if re.search(sstr, part):
                sstr = r'run_until_complete|run_forever|create_task|NamedTask'
                if re.search(sstr, part):
                    continue
                print('Please review line {}: async function "{}" is passed to a function.'.format(lnum, task))
                print(opart)
                print()
                good = False
                continue
            # func(mytask, more_args) may or may not be an error
            sstr = ''.join((r'.*\w+[ \t]*\([ \t]*', task, r'[ \t]*[^\(]'))
            if re.search(sstr, part):
                print('Please review line {}: async function "{}" is passed to a function.'.format(lnum, task))
                print(opart)
                print()
                good = False
                continue

            # Might be a method. Discard object.
            sstr = ''.join((r'.*\w+[ \t]*\([ \t]*\w+\.', task))
            if re.search(sstr, part):
                continue
            print('Please review line {}: async function "{}" is not awaited.'.format(lnum, task))
            print(opart)
            print()
            good = False
    return good

txt = '''check_async_code.py
usage: check_async_code.py sourcefile.py

This rather crude script is designed to locate a single type of coding error
which leads to silent runtime failure and hence can be hard to locate.

It is intended to be used on otherwise correct source files and is not robust
in the face of syntax errors. Use pylint or other tools for general syntax
checking.

It assumes code is written in the style advocated in the tutorial where coros
are declared with "async def".

Under certain circumstances it can produce false positives. In some cases this
is by design. Given an asynchronous function foo the following is correct:
loop.run_until_complete(foo())
The following line may or may not be an error depending on the design of bar()
bar(foo, args)
Likewise asynchronous functions can be put into objects such as dicts, lists or
sets. You may wish to review such lines to check that the intention was to put
the function rather than its result into the object.

A false positive which is a consequence of the hacky nature of this script is
where a task has the same name as a synchronous bound method of some class. A
call to the bound method will produce an erroneous warning. This is because the
code does not parse class definitions.

In practice the odd false positive is easily spotted in the code.
'''

def usage(code=0):
    print(txt)
    sys.exit(code)

# Process a line
in_triple_quote = False
def do_line(line, passn, lnum):
    global in_triple_quote
    ignore = False
    good = True
    # TODO The following isn't strictly correct. A line might be of the form
    # erroneous Python ; ''' start of string
    # It could therefore miss the error.
    if re.search(r'[^"]*"""|[^\']*\'\'\'', line):
        if in_triple_quote:
            # Discard rest of line which terminates triple quote
            ignore = True
        in_triple_quote = not in_triple_quote
    if not in_triple_quote and not ignore:
        parts = line.split(';')
        for part in parts:
            # discard comments and whitespace at start and end
            part = part.split('#')[0].strip()
            if part:
                good &= passn(part, lnum)
    return good

def main(fn):
    global in_triple_quote
    good = True
    try:
        with open(fn, 'r') as f:
            for passn in (pass1, pass2):
                in_triple_quote = False
                lnum = 1
                for line in f:
                    good &= do_line(line, passn, lnum)
                    lnum += 1
                f.seek(0)

    except FileNotFoundError:
        print('File {} does not exist.'.format(fn))
        return
    if good:
        print('No errors found!')

if __name__ == "__main__":
    if len(sys.argv) !=2:
        usage(1)
    arg = sys.argv[1].strip()
    if arg == '--help' or arg == '-h':
        usage()
    main(arg)
