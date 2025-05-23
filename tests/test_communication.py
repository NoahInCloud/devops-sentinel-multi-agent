import pytest
from src.communication.a2a_protocol import A2AProtocol
from src.communication.websocket_handler import WebSocketHandler
from src.communication.message_queue import MessageQueue

@pytest.fixture
def setup_communication():
    a2a_protocol = A2AProtocol()
    websocket_handler = WebSocketHandler()
    message_queue = MessageQueue()
    return a2a_protocol, websocket_handler, message_queue

def test_a2a_protocol_initialization(setup_communication):
    a2a_protocol, _, _ = setup_communication
    assert a2a_protocol is not None

def test_websocket_handler_initialization(setup_communication):
    _, websocket_handler, _ = setup_communication
    assert websocket_handler is not None

def test_message_queue_initialization(setup_communication):
    _, _, message_queue = setup_communication
    assert message_queue is not None

def test_a2a_protocol_send_message(setup_communication):
    a2a_protocol, _, _ = setup_communication
    result = a2a_protocol.send_message("test_agent", "Hello")
    assert result is True

def test_websocket_handler_send_message(setup_communication):
    _, websocket_handler, _ = setup_communication
    result = websocket_handler.send_message("Hello")
    assert result is True

def test_message_queue_enqueue_dequeue(setup_communication):
    _, _, message_queue = setup_communication
    message_queue.enqueue("test_message")
    assert message_queue.dequeue() == "test_message"