from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json


# TODO: Refactoring needed
from django.core.serializers.json import DjangoJSONEncoder


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = "chat_%s" % self.room_name

        print("Connected to " + self.room_group_name)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        print('message from WebSocket: ' + message)

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'console_message',
                'message': message
            }
        )

    def console_message(self, event):
        message = event['message']
        message_type = event['message_type']
        datetime = event['datetime']

        print('message from room group: ' + message + message_type + datetime)

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message,
            'message_type': message_type,
            'datetime': datetime
        }))


# TODO: Refactoring needed
class InternalConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = "internal_%s" % self.room_name

        print("Connected to " + self.room_group_name)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        print('message from client: ' + message)
        # TODO: not implemented yet!

    def task_end(self, event):
        self.send(text_data=json.dumps(event))

    def completed_table(self, event):
        self.send(text_data=json.dumps(event))

    def started_phase(self, event):
        self.send(text_data=json.dumps(event))

    def completed_phase(self, event):
        self.send(text_data=json.dumps(event))

    def started_process_all(self, event):
        self.send(text_data=json.dumps(event))

    def table_state_changed(self, event):
        self.send(text_data=json.dumps(event))

    def import_progress(self, event):
        self.send(text_data=json.dumps(event))

    def import_status(self, event):
        self.send(text_data=json.dumps(event))

    def delete_all_finished(self, event):
        self.send(text_data=json.dumps(event))
