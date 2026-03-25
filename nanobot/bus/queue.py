"""Async message queue for decoupled channel-agent communication."""

import asyncio
from typing import Optional

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.security.encryption import TransportEncryption


class MessageBus:
    """
    Async message bus that decouples chat channels from the agent core.

    Channels push messages to the inbound queue, and the agent processes
    them and pushes responses to the outbound queue.
    
    Supports optional end-to-end encryption for message transport.
    """

    def __init__(self, transport_encryption: Optional[TransportEncryption] = None):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self.transport_encryption = transport_encryption

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """
        Publish a message from a channel to the agent.
        
        If transport encryption is enabled, the message content will be encrypted.
        """
        if self.transport_encryption and self.transport_encryption.enabled:
            encrypted_content, updated_metadata = self.transport_encryption.encrypt_message(
                msg.content, msg.metadata.copy()
            )
            encrypted_msg = InboundMessage(
                channel=msg.channel,
                sender_id=msg.sender_id,
                chat_id=msg.chat_id,
                content=encrypted_content,
                timestamp=msg.timestamp,
                media=msg.media,
                metadata=updated_metadata,
                session_key_override=msg.session_key_override,
            )
            await self.inbound.put(encrypted_msg)
        else:
            await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """
        Consume the next inbound message (blocks until available).
        
        If the message is encrypted, it will be automatically decrypted.
        """
        msg = await self.inbound.get()
        if self.transport_encryption and self.transport_encryption.enabled:
            decrypted_content = self.transport_encryption.decrypt_message(
                msg.content, msg.metadata
            )
            if decrypted_content != msg.content:
                return InboundMessage(
                    channel=msg.channel,
                    sender_id=msg.sender_id,
                    chat_id=msg.chat_id,
                    content=decrypted_content,
                    timestamp=msg.timestamp,
                    media=msg.media,
                    metadata=msg.metadata,
                    session_key_override=msg.session_key_override,
                )
        return msg

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """
        Publish a response from the agent to channels.
        
        If transport encryption is enabled, the message content will be encrypted.
        """
        if self.transport_encryption and self.transport_encryption.enabled:
            encrypted_content, updated_metadata = self.transport_encryption.encrypt_message(
                msg.content, msg.metadata.copy()
            )
            encrypted_msg = OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=encrypted_content,
                reply_to=msg.reply_to,
                media=msg.media,
                metadata=updated_metadata,
            )
            await self.outbound.put(encrypted_msg)
        else:
            await self.outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """
        Consume the next outbound message (blocks until available).
        
        If the message is encrypted, it will be automatically decrypted.
        """
        msg = await self.outbound.get()
        if self.transport_encryption and self.transport_encryption.enabled:
            decrypted_content = self.transport_encryption.decrypt_message(
                msg.content, msg.metadata
            )
            if decrypted_content != msg.content:
                return OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=decrypted_content,
                    reply_to=msg.reply_to,
                    media=msg.media,
                    metadata=msg.metadata,
                )
        return msg

    @property
    def inbound_size(self) -> int:
        """Number of pending inbound messages."""
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        """Number of pending outbound messages."""
        return self.outbound.qsize()
