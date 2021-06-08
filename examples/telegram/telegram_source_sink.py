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

# Receive message from a Telegram bot. If the message content is `hi`
# or `Hi`, create a new stream with a telegram sink attached to it and
# respond to the bot with a `Hello <username>`. If the bot sends an `exit`
# message then this application will end, otherwise it will continue
# receiving any messages sent to the Telegram bot.

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


# Ray actor to handle events
@ray.remote
class TelegramMessageHandler:
    def __init__(self):
        self.chat_id = ""
        self.last_message = ""
        self.sender_name = ""
        self.last_message_read = False

    def append(self, event):
        parsed_event = json.loads(event)

        # Safely extract desired values.
        from_value = ""
        if 'from' in parsed_event:
            from_value = parsed_event['from']

        first_name = "N/A"
        if 'first_name' in from_value:
            first_name = from_value['first_name']

        id_value = "N/A"
        if 'id' in from_value:
            id_value = from_value['id']

        message = "N/A"
        if 'text' in parsed_event:
            message = parsed_event['text']

        # Log message received.
        print('FROM', first_name, ":", message)

        # Update state.
        self.sender_name = first_name
        self.last_message = message
        self.chat_id = id_value
        self.last_message_read = False

    def get_last_message(self):
        self.last_message_read = True
        return self.last_message

    def get_chat_id(self):
        return self.chat_id

    def get_sender_name(self):
        return self.sender_name

    def message_read(self):
        return self.last_message_read


# Instantiate the message handler.
message_handler = TelegramMessageHandler.remote()

# Log all events from stream-attached sources.
stream >> message_handler

# Create a stream to reply back to the Telegram chat. The sink
# attached to this stream will depend on the chat ID hence when
# the chat ID changes then a new sink will have to be created
# and the old one will have to be deleted. The reply always goes
# back to the chat where the hello originted from.
reply_stream = rayvens.Stream('reply-to-telegram')

# Keep track of chat IDs and the sinks.
chat_id_to_sink = {}
current_message = ""
while True:
    # If the last message has already been read.
    if ray.get(message_handler.message_read.remote()):
        time.sleep(1)
        continue

    # Read new message:
    current_message = ray.get(message_handler.get_last_message.remote())

    # When someone says hi, say hello back.
    if current_message in ["hi", "Hi"]:
        chat_id = ray.get(message_handler.get_chat_id.remote())

        if chat_id not in chat_id_to_sink:
            # Create sink.
            sink_config = dict(kind='telegram-sink',
                               authorization_token=authorization_token,
                               chat_id=chat_id)

            # Disconnect all sinks:
            reply_stream.disconnect_all()
            chat_id_to_sink = {}

            # Add a new sink:
            sink = reply_stream.add_sink(sink_config)

            # Save sink to map:
            chat_id_to_sink[chat_id] = sink

        # Say hello back:
        sender_name = ray.get(message_handler.get_sender_name.remote())
        reply_stream << f"Hello {sender_name}"

    elif current_message in ["exit", "Exit"]:
        # Disconnect all sinks:
        reply_stream.disconnect_all()
        chat_id_to_sink = {}
        break

# Wait before ending program to ensure all messages are marked as processed.
time.sleep(5)

stream.disconnect_all()
