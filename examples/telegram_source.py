#
# Copyright IBM Corporation 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import ray
import rayvens
import time
import sys
import json

# Receive message from a Telegram bot.

# To set up a Telegram bot visit the @BotFather chat on Telegram.

# Initialize ray.
if len(sys.argv) < 3:
    print(f'usage: {sys.argv[0]} <authorization_token> <run_mode>')
    sys.exit(1)
authorization_token = sys.argv[1]
run_mode = sys.argv[2]
if run_mode not in ['local', 'operator']:
    raise RuntimeError(f'Invalid run mode provided: {run_mode}')

# Initialize ray either on the cluster or locally otherwise.
if run_mode == 'operator':
    ray.init(address='auto')
else:
    ray.init()

# Start rayvens in the desired mode.
rayvens.init(mode=run_mode)

# Create stream.
stream = rayvens.Stream('telegram')

# Event source config.
source_config = dict(kind='telegram-source',
                     authorization_token=authorization_token)

# Attach source to stream.
source = stream.add_source(source_config)


# Function used to process the event received from the Telegram bot.
def telegram_message_processor(event):
    parsed_event = json.loads(event)
    print('FROM', parsed_event['from']['first_name'], ":",
          parsed_event['text'])


# Log all events from stream-attached sources.
stream >> telegram_message_processor

# Wait before ending program.
time.sleep(100)

stream.disconnect_all()
