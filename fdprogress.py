#!/usr/bin/env python3
import argparse
import os
import time
import shutil
import sys
import math
import stat

if sys.version_info.major != 3:
    print("Python 3 required")
    sys.exit(2)

def round_down(n, d=8):
    # https://stackoverflow.com/a/43533589/119527
    d = 10 ** d
    return math.floor(n * d) / d

def human_size(n, decimal_places=2):
    # https://gist.github.com/JonathonReinhart/6839e16a38258c6b8f25bc9046199ccb
    n = float(n)

    suffixes = ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi']
    for suffix in suffixes:
        if n < 1024:
            break
        n /= 1024

    if n.is_integer():
        size = str(int(n))
    else:
        size = '{0:.{1}f}'.format(round_down(n, decimal_places), decimal_places)

    return '{} {}B'.format(size, suffix)


class ProgressBar(object):
    # ProgressBar originally taken from clint
    # (https://github.com/kennethreitz/clint)
    #
    # Copyright (c) 2011, Kenneth Reitz <me@kennethreitz.com>
    #
    # Permission to use, copy, modify, and/or distribute this software for any
    # purpose with or without fee is hereby granted, provided that the above
    # copyright notice and this permission notice appear in all copies.
    TEMPLATE = '%s[%s%s] %s/%s (%f%%) - %s\r'

    # How long to wait before recalculating the ETA
    ETA_INTERVAL = 1

    # How many intervals (excluding the current one) to calculate the simple moving
    # average
    ETA_SMA_WINDOW = 9

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.done()
        return False  # we're not suppressing exceptions

    def __init__(self, label='', width=None, hide=None, empty_char=' ',
                 filled_char='#', expected_size=None, every=1,
                 stream=sys.stderr):
        self.label = label
        self.stream = stream

        self.hide = hide
        # Only show bar in terminals by default (better for piping, logging etc.)
        if hide is None:
            try:
                self.hide = not self.stream.isatty()
            except AttributeError:  # output does not support isatty()
                self.hide = True
        self.empty_char =    empty_char
        self.filled_char =   filled_char
        self.expected_size = expected_size
        self.every =         every
        self.start =         time.time()
        self.ittimes =       []
        self.eta =           0
        self.etadelta =      time.time()
        self.etadisp =       self.format_time(self.eta)
        self.last_progress = 0

        # Auto-calculate width
        if width is None:
            ts = shutil.get_terminal_size((80, 40))
            test = self.TEMPLATE % (
                    self.label, '', '',
                    human_size(self.expected_size), human_size(self.expected_size),
                    100.0,
                    self.format_time(0))
            width = ts.columns - len(test)
        self.width = width

        if (self.expected_size):
            self.show(0)

    def show(self, progress, count=None):
        if count is not None:
            self.expected_size = count
        if self.expected_size is None:
            raise Exception("expected_size not initialized")
        self.last_progress = progress
        if (time.time() - self.etadelta) > self.ETA_INTERVAL:
            self.etadelta = time.time()
            self.ittimes = \
                self.ittimes[-self.ETA_SMA_WINDOW:] + \
                    [-(self.start - time.time()) / (progress+1)]
            self.eta = \
                sum(self.ittimes) / float(len(self.ittimes)) * \
                (self.expected_size - progress)
            self.etadisp = self.format_time(self.eta)
        x = int(self.width * progress / self.expected_size)
        if not self.hide:
            if ((progress % self.every) == 0 or      # True every "every" updates
                (progress == self.expected_size)):   # And when we're done
                self.stream.write(self.TEMPLATE % (
                    self.label, self.filled_char * x,
                    self.empty_char * (self.width - x),
                    human_size(progress), human_size(self.expected_size),
                    self.percent(progress),
                    self.etadisp))
                self.stream.flush()

    def done(self):
        self.elapsed = time.time() - self.start
        elapsed_disp = self.format_time(self.elapsed)
        if not self.hide:
            # Print completed bar with elapsed time
            self.stream.write(self.TEMPLATE % (
                self.label, self.filled_char * self.width,
                self.empty_char * 0,
                self.last_progress,
                self.expected_size, 
                self.percent(self.last_progress),
                elapsed_disp))
            self.stream.write('\n')
            self.stream.flush()

    def percent(self, progress):
        progress = self.last_progress
        return float(progress) / self.expected_size * 100.0

    def format_time(self, seconds):
        return time.strftime('%H:%M:%S', time.gmtime(seconds))

class FdInfo:
    def __str__(self):
        return '{}({})'.format(
                self.__class__.__name__,
                ', '.join('{}={!r}'.format(k,v) for k,v in self.__dict__.items()))

    def __repr__(self):
        return str(self)

    @property
    def openmode(self):
        return self.flags & 0b11

    @property
    def readable(self):
        return self.openmode in (os.O_RDONLY, os.O_RDWR)

    @property
    def writable(self):
        return self.openmode in (os.O_WRONLY, os.O_RDWR)

    @property
    def modestr(self):
        return {
            os.O_RDONLY: 'r-',
            os.O_WRONLY: '-w',
            os.O_RDWR:   'rw',
        }[self.openmode]

    @classmethod
    def get(cls, pid, fd):
        fdpath = '/proc/{pid}/fd/{fd}'.format(pid=pid, fd=fd)

        info = cls()
        info.target = os.readlink(fdpath)
        info.stat = os.stat(fdpath, follow_symlinks=True)

        fields = {
            'pos':      lambda v: int(v, 10),
            'flags':    lambda v: int(v, 8),
            'mnt_id':   lambda v: int(v, 10),
        }

        with open('/proc/{pid}/fdinfo/{fd}'.format(pid=pid, fd=fd)) as f:
            for line in f:
                name, val = (s.strip() for s in line.split(':', 1))
                t = fields.get(name, lambda v: v)
                setattr(info, name, t(val))

        return info

    @classmethod
    def get_all(cls, pid):
        result = {}
        for ent in os.listdir('/proc/{pid}/fd'.format(pid=pid)):
            fd = int(ent)
            result[fd] = cls.get(pid, fd)
        return result

    @property
    def filetype(self):
        modes = (
            (stat.S_ISDIR,  'dir'),
            (stat.S_ISCHR,  'chr'),
            (stat.S_ISBLK,  'blk'),
            (stat.S_ISREG,  'reg'),
            (stat.S_ISFIFO, 'fifo'),
            (stat.S_ISLNK,  'lnk'),
            (stat.S_ISSOCK, 'sock'),
            (stat.S_ISDOOR, 'door'),
            (stat.S_ISPORT, 'port'),
            (stat.S_ISWHT,  'wht'),
        )
        for meth, mode in modes:
            if meth(self.stat.st_mode):
                return mode
        return '???'

    @property
    def filesize(self):
        return self.stat.st_size


def get_proc_name(pid):
    path = '/proc/{pid}/comm'.format(pid=pid)
    with open(path, 'r') as f:
        return f.read().strip()


def prompt_for_fd(pid):
    fdinfos = FdInfo.get_all(pid)

    print("Open file descriptors for PID {} (* = good candidate):".format(pid))
    for fd, info in sorted(fdinfos.items()):
        print('{good} {fd}  {rw}:  {target}{type}'.format(
            fd = fd,
            rw = info.modestr,
            target = info.target,
            type = '' if info.filetype == 'reg' else ' ({})'.format(info.filetype),
            good = '*' if (info.readable and info.filetype == 'reg') else ' ',
            ))

    # Only interact if stdin connected to a tty
    if not sys.stdin.isatty():
        raise SystemExit("Error: File descriptor required.")

    while True:
        reply = input('fd to monitor: ').strip()
        if not reply:
            continue
        try:
            fd = int(reply)
        except ValueError:
            print('Invalid integer: ', reply)
            continue

        if not fd in fdinfos:
            print('fd {} not open'.format(fd))
            continue

        return fd


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', type=int)
    ap.add_argument('fd', type=int, nargs='?')
    return ap.parse_args()


def main():
    args = parse_args()

    # If fd is not given, list open fds
    if args.fd is None:
        args.fd = prompt_for_fd(args.pid)

    info = FdInfo.get(args.pid, args.fd)

    if info.filetype != 'reg':
        raise SystemExit("fd must refer to a regular file")

    print("{comm} ({pid}) progress on {target}:".format(
        comm = get_proc_name(args.pid),
        pid = args.pid,
        target = info.target,
        ))

    with ProgressBar(expected_size=info.filesize, filled_char='\u2588') as bar:
        while True:
            info = FdInfo.get(pid=args.pid, fd=args.fd)
            bar.show(info.pos)
            time.sleep(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
