import threading
import kivy
from kivy.uix.gridlayout import GridLayout

import bptc.networking.utils as network_utils

kivy.require('1.0.7')


class Client(GridLayout):
    def __init__(self, network):
        self.defaults = {
            'listening_port': 8000,
            'registering_address': 'localhost:8000',
            'members_address': 'localhost:8001',
            'member_id': 'Some-ID',
            'push_address': 'localhost:8000',
        }
        self.network = network
        self.hashgraph = network.hashgraph
        self.me = network.hashgraph.me
        self.defaults['member_id'] = self.me.verify_key[:6] + '...'
        self.stop = threading.Event()
        super().__init__()

    # Get value for an attribute from its input element
    def get(self, key):
        for id_, obj in self.ids.items():
            if id_ == key:
                return obj.text

    def start_listening(self):
        network_utils.start_listening(self.network, self.get('listening_port'))

    def register(self):
        ip, port = self.get('registering_address').split(':')
        network_utils.register(self.me.id, self.get('listening_port'), ip, port)

    def query_members(self):
        ip, port = self.get('members_address').split(':')
        network_utils.query_members(self, ip, port)

    def heartbeat(self):
        self.network.heartbeat()

    def push(self):
        ip, port = self.get('push_address').split(':')
        self.network.push_to(ip, int(port))

    def push_random(self):
        self.network.push_to_random()

    def generate_limited_input(self, widget, n):
        # This is used for limiting the input length
        return lambda text, from_undo: text[:n - len(widget.text)]

    def get_widget_id(self, widget):
        for id_, obj in self.ids.items():
            if obj == widget:
                return id_
        return None
