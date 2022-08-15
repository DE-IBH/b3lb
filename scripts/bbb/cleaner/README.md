# cleaner

The *cleaner* service is recommended by *b3lb* to kill orphan bbb meetings with a daily systemd timer.
Any meeting running longer than `MEETING_TIMEOUT`.


## Setup

- put `cleaner.py` script at `/opt/b3lb/scripts`
- consider to change `MEETING_TIMEOUT`
- enable the `b3lb-cleaner.timer` unit:
  - put `b3lb-cleaner.service` at `/etc/systemd/system`
  - put `b3lb-cleaner.timer` at `/etc/systemd/system`
  - reload *systemd* using `systemctl daemon-reload`
  - enable unit using `systemctl enable b3lb-cleaner.timer`
  - start unit using `systemctl start b3lb-cleaner.timer`
