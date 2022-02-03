#!/usr/bin/ruby
# encoding: UTF-8

# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2022 IBH IT-Service GmbH
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
# for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

require "optimist"
require "java_properties"
require "sqlite3"
require File.expand_path('../../../lib/recordandplayback', __FILE__)

properties_fn = "/etc/b3lb/push.properties"
props = JavaProperties::Properties.new(properties_fn)


opts = Optimist::options do
  opt :meeting_id, "Meeting id to archive", :type => String
  opt :format, "Playback format name", :type => String
end
meeting_id = opts[:meeting_id]

logger = Logger.new("/var/log/bigbluebutton/b3lb_push_hook.log", 'weekly' )
logger.level = Logger::INFO
BigBlueButton.logger = logger

published_files = "#{props[:publishedFolder]}/#{meeting_id}"


def get_metadata(key, meeting_metadata)
  meeting_metadata.key?(key) ? meeting_metadata[key].value : nil
end


BigBlueButton.logger.info("[#{meeting_id}] start")

begin
  nonce_tag = props[:nonceMetaTag]
  queue_fn = "#{props[:queueDirname]}/#{props[:queueFilename]}"

  meeting_metadata = BigBlueButton::Events.get_meeting_metadata("/var/bigbluebutton/recording/raw/#{meeting_id}/events.xml")
  nonce = get_metadata(nonce_tag, meeting_metadata)

  unless nonce.nil?
    BigBlueButton.logger.info("[#{meeting_id}] meta tag #{nonce_tag} found, queueing...")

    db = SQLite3::Database.open queue_fn
    db.execute "CREATE TABLE IF NOT EXISTS backlog (mid varchar(64), nonce varchar(64))"
    db.execute "INSERT INTO backlog (mid, nonce) VALUES (?, ?)", meeting_id, nonce
  end

rescue => e
  BigBlueButton.logger.info("[#{meeting_id}] ERROR: #{e.to_s}")
end

BigBlueButton.logger.info("[#{meeting_id}] finished")

exit 0
