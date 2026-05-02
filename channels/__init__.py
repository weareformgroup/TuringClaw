"""Chat channels module with plugin architecture."""

from TuringClaw.channels.base import BaseChannel
from TuringClaw.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
