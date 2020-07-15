# synctest.py Demo of synchronous code scheduling tasks with cron

# Copyright (c) 2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

from .cron import cron
from time import localtime, sleep, time

def foo(txt):
    yr, mo, md, h, m, s, wd = localtime()[:7]
    fst = "{} {:02d}:{:02d}:{:02d} on {:02d}/{:02d}/{:02d}"
    print(fst.format(txt, h, m, s, md, mo, yr))

def main():
    print('Synchronous test running...')
    tasks = []  # Entries: cron, callback, args, one_shot
    cron4 = cron(hrs=None, mins=range(0, 60, 4))
    tasks.append([cron4, foo, ('every 4 mins',), False, False])
    cron5 = cron(hrs=None, mins=range(0, 60, 5))
    tasks.append([cron5, foo, ('every 5 mins',), False, False])
    cron3 = cron(hrs=None, mins=range(0, 60, 3))
    tasks.append([cron3, foo, ('every 3 mins',), False, False])
    cron2 = cron(hrs=None, mins=range(0, 60, 2))
    tasks.append([cron2, foo, ('one shot',), True, False])
    to_run = []
    while True:
        now = int(time())  # Ensure constant: get once per iteration.
        tasks.sort(key=lambda x:x[0](now))
        to_run.clear()  # Pending tasks
        deltat = tasks[0][0](now)  # Time to pending task(s)
        for task in (t for t in tasks if t[0](now) == deltat):  # Tasks with same delta t
            to_run.append(task)
            task[4] = True  # Has been scheduled
        # Remove on-shot tasks which have been scheduled
        tasks = [t for t in tasks if not (t[3] and t[4])]
        sleep(deltat)
        for tsk in to_run:
            tsk[1](*tsk[2])
        sleep(1.2)  # Ensure seconds have rolled over

main()
