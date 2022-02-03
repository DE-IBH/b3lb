# BBB Recording Uploader

The *b3lb-push* service is required to upload BBB recordings from the nodes to the *b3lb* backend.


## Setup

- install ruby sqlite3 gem: `apt-get install ruby-sqlite3`
- copy `b3lb-push-hook.rb` to `/usr/local/bigbluebutton/core/scripts/post_publish`
- copy `b3lb-push` to `/usr/local/lib/b3lb`
- create directory `/etc/b3lb`
- copy and edit `push.properties` to `/etc/b3lb`
- enable `b3lb-push` systemd units:
  - copy `b3lb-push.{service,path,timer}` to `/etc/systemd/system`
  - reload *systemd* using `systemctl daemon-reload`
  - enable *b3lb-push* unit using `systemctl enable b3lb-push.path b3lb-push.timer`
  - start *b3lb-push* unit using `systemctl start b3lb-push.path b3lb-push.timer`
