# loadcalc

The *loadcalc* service is required by *b3lb* to get the CPU load of a BBB backend node.


## Setup

- put `load.nginx` at `/etc/bigbluebutton/nginx/` and reload *nginx*
  - consider to add some nginx acl if you do not want to expose the load value
- put `load.py` script at `/srv/loadcalc`
- enable `loadcalc.service` unit file:
  - put `loadcalc.service` at `/etc/systemd/system`
  - reload *systemd* using `systemctl daemon-reload`
  - enable *loadcalc* unit using `systemctl enable loadcalc.service`
  - start *loadcalc* unit using `systemctl start loadcalc.service`


## Verify

Accessing the node's load URL should return a single integer value:

```bash
$ curl https://n1337.bbbconf.de/b3lb/load
57
```
