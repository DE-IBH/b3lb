# BBB Node CPU Load Calculation

The *b3lb-load* service is required by *b3lb* to get the CPU load of the BBB backend nodes.


## Setup

- put `b3lb-load.nginx` at `/etc/bigbluebutton/nginx/` and reload *nginx*
  - consider to add some nginx acl if you do not want to expose the load value
- put `b3lb-load` at `/usr/local/lib/b3lb`
- enable `b3lb-load.service` unit file:
  - put `b3lb-load.service` at `/etc/systemd/system`
  - reload *systemd* using `systemctl daemon-reload`
  - enable *b3lb-load* unit using `systemctl enable b3lb-load.service`
  - start *b3lb-load* unit using `systemctl start b3lb-load.service`


## Verify

Accessing the node's load URL should return a single integer value:

```bash
$ curl https://n1337.bbbconf.de/b3lb/load
57
```
