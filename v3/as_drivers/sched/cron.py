# cron.py

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

from time import mktime, localtime
# Validation
_valid = ((0, 59, 'secs'), (0, 59, 'mins'), (0, 23, 'hrs'),
          (1, 31, 'mday'), (1, 12, 'month'), (0, 6, 'wday'))
_mdays = {2:28, 4:30, 6:30, 9:30, 11:30}
# A call to the inner function takes 270-520μs on Pyboard depending on args
def cron(*, secs=0, mins=0, hrs=3, mday=None, month=None, wday=None):
    # Given an arg and current value, return offset between arg and cv
    # If arg is iterable return offset of next arg +ve for future -ve for past (add modulo)
    def do_arg(a, cv):  # Arg, current value
        if a is None:
            return 0
        elif isinstance(a, int):
            return a - cv
        try:
            return min(x for x in a if x >= cv) - cv
        except ValueError:  # wrap-round
            return min(a) - cv  # -ve
        except TypeError:
            raise ValueError('Invalid argument type', type(a))

    if secs is None:  # Special validation for seconds
        raise ValueError('Invalid None value for secs')
    if not isinstance(secs, int) and len(secs) > 1:  # It's an iterable
        ss = sorted(secs)
        if min((a[1] - a[0] for a in zip(ss, ss[1:]))) < 2:
            raise ValueError("Can't have consecutive seconds.", last, x)
    args = (secs, mins, hrs, mday, month, wday)  # Validation for all args
    valid = iter(_valid)
    vestr = 'Argument {} out of range'
    vmstr = 'Invalid no. of days for month'
    for arg in args:  # Check for illegal arg values
        lower, upper, errtxt = next(valid)
        if isinstance(arg, int):
            if not lower <= arg <= upper:
                raise ValueError(vestr.format(errtxt))
        elif arg is not None:  # Must be an iterable
            if any(v for v in arg if not lower <= v <= upper):
                raise ValueError(vestr.format(errtxt))
    if mday is not None and month is not None:  # Check mday against month
        max_md = mday if isinstance(mday, int) else max(mday)
        if isinstance(month, int):
            if max_md > _mdays.get(month, 31):
                raise ValueError(vmstr)
        elif sum((m for m in month if max_md > _mdays.get(m, 31))):
            raise ValueError(vmstr)
    if mday is not None and wday is not None and do_arg(mday, 23) > 0:
        raise ValueError('mday must be <= 22 if wday also specified.')

    def inner(tnow):
        tev = tnow  # Time of next event: work forward from time now
        yr, mo, md, h, m, s, wd = localtime(tev)[:7]
        init_mo = mo  # Month now
        toff = do_arg(secs, s)
        tev += toff if toff >= 0 else 60 + toff

        yr, mo, md, h, m, s, wd = localtime(tev)[:7]
        toff = do_arg(mins, m)
        tev += 60 * (toff if toff >= 0 else 60 + toff)

        yr, mo, md, h, m, s, wd = localtime(tev)[:7]
        toff = do_arg(hrs, h)
        tev += 3600 * (toff if toff >= 0 else 24 + toff)

        yr, mo, md, h, m, s, wd = localtime(tev)[:7]
        toff = do_arg(month, mo)
        mo += toff
        md = md if mo == init_mo else 1
        if toff < 0:
            yr += 1
        tev = mktime((yr, mo, md, h, m, s, wd, 0))
        yr, mo, md, h, m, s, wd = localtime(tev)[:7]
        if mday is not None:
            if mo == init_mo:  # Month has not rolled over or been changed
                toff = do_arg(mday, md)  # see if mday causes rollover
                md += toff
                if toff < 0:
                    toff = do_arg(month, mo + 1)  # Get next valid month
                    mo += toff + 1  # Offset is relative to next month
                    if toff < 0:
                        yr += 1
            else:  # Month has rolled over: day is absolute
                md = do_arg(mday, 0)

        if wday is not None:
            if mo == init_mo:
                toff = do_arg(wday, wd)
                md += toff % 7  # mktime handles md > 31 but month may increment
                tev = mktime((yr, mo, md, h, m, s, wd, 0))
                cur_mo = mo
                _, mo = localtime(tev)[:2]  # get month
                if mo != cur_mo:
                    toff = do_arg(month, mo)  # Get next valid month
                    mo += toff  # Offset is relative to new, incremented month
                    if toff < 0:
                        yr += 1
                    tev = mktime((yr, mo, 1, h, m, s, wd, 0))  # 1st of new month
                    yr, mo, md, h, m, s, wd = localtime(tev)[:7]  # get day of week
                    toff = do_arg(wday, wd)
                    md += toff % 7
            else:
                md = 1 if mday is None else md
                tev = mktime((yr, mo, md, h, m, s, wd, 0))  # 1st of new month
                yr, mo, md, h, m, s, wd = localtime(tev)[:7]  # get day of week
                md += (do_arg(wday, 0) - wd) % 7

        return mktime((yr, mo, md, h, m, s, wd, 0)) - tnow
    return inner
