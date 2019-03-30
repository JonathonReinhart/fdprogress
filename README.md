fdprogress
==========
A stupid utility for watching a process's progress reading a file descriptor.

```
$ pip install fdprogress

$ fdprogress $(pidof cp)
Open file descriptors for PID 5034 (* = good candidate):
  0  rw:  /dev/pts/3 (chr)
  1  rw:  /dev/pts/3 (chr)
  2  rw:  /dev/pts/3 (chr)
* 3  r-:  /home/jreinhart/bigfile
  4  -w:  /home/jreinhart/bigfile-copy
fd to monitor: 3
cp (5034) progress on /home/jreinhart/bigfile:
[████████████████████                                        ]   20.1 GiB/60.7 GiB (33.11%) - 00:04:41
```
