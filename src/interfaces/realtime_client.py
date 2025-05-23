from azure.communication.callautomation import CallAutomationClient
from azure.communication.callautomation.aio import CallAutomationClient as AsyncCallAutomationClient
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureRealtimeExecutionSettings
from semantic_kernel.connectors.ai.open_ai.services._open_ai_realtime import ListenEvents
from semantic_kernel.connectors.ai.realtime_client_base import RealtimeClientBase
from quart import websocket
import asyncio
import json

class RealtimeClient:
    def __init__(self, connection_string: str):
        self.acs_client = CallAutomationClient.from_connection_string(connection_string)
        self.kernel = Kernel()

    async def handle_realtime_messages(self, client: RealtimeClientBase):
        async for event in client.receive():
            if event.service_type == ListenEvents.SESSION_CREATED:
                print("Session Created")
            elif event.service_type == ListenEvents.ERROR:
                print(f"Error: {event.service_event.error}")
            elif event.service_type == ListenEvents.RESPONSE_DONE:
                print("Response Done")
                print(f"Response Id: {event.service_event.response.id}")

    async def from_acs_to_realtime(self, client: RealtimeClientBase):
        while True:
            try:
                stream_data = await websocket.receive()
                data = json.loads(stream_data)
                if data["kind"] == "AudioData":
                    await client.send(event=data)
            except Exception:
                break

    async def start_realtime_session(self):
        client = AzureRealtimeWebsocket()
        settings = AzureRealtimeExecutionSettings(
            instructions="You are a chat bot.",
            turn_detection={"type": "server_vad"},
            voice="shimmer",
            input_audio_format="pcm16",
            output_audio_format="pcm16",
        )

        async with client(settings=settings, create_response=True, kernel=self.kernel):
            receive_task = asyncio.create_task(self.handle_realtime_messages(client))
            await self.from_acs_to_realtime(client)
            receive_task.cancel()