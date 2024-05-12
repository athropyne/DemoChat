from __future__ import annotations

import datetime

from sqlalchemy import Table, MetaData, Column, String, Integer, Date, ForeignKey, Enum, DateTime

from services.accounts.aliases import AccountAliases
from services.messages.aliases import PublicAliases
from services.rooms.aliases import LocalRanks, RoomAliases, LocalRankAliases

metadata = MetaData()
accounts = Table(
    "accounts",
    metadata,
    Column(AccountAliases.ID, Integer, primary_key=True, autoincrement=True),
    Column(AccountAliases.nickname, String(16), unique=True, nullable=False),
    Column(AccountAliases.password, String(100), nullable=False),
    Column(AccountAliases.created_at, Date, nullable=False, default=datetime.date.today())
)

rooms = Table(
    "rooms",
    metadata,
    Column(RoomAliases.ID, Integer, primary_key=True, autoincrement=True),
    Column(RoomAliases.title, String(24), unique=True, nullable=False),
    Column(RoomAliases.created_at, Date, nullable=False, default=datetime.date.today())
)

locations = Table(
    "locations",
    metadata,
    Column(AccountAliases.ID, ForeignKey(accounts.c[AccountAliases.ID], ondelete="CASCADE", onupdate="CASCADE"), nullable=False),
    Column(RoomAliases.ID, ForeignKey(rooms.c[RoomAliases.ID], ondelete="CASCADE", onupdate="CASCADE"), nullable=True, default=None),
)

local_ranks = Table(
    "local_ranks",
    metadata,
    Column(AccountAliases.ID, ForeignKey(accounts.c[AccountAliases.ID], onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    Column(RoomAliases.ID, ForeignKey(rooms.c[RoomAliases.ID], onupdate="CASCADE", ondelete="CASCADE"), nullable=False),
    Column(LocalRankAliases.rank, Enum(LocalRanks), nullable=True)
)

public = Table(
    "public",
    metadata,
    Column(PublicAliases.ID, Integer, primary_key=True),
    Column(PublicAliases.creator, ForeignKey(accounts.c[AccountAliases.ID], onupdate="CASCADE", ondelete="NO ACTION"), nullable=False),
    Column(PublicAliases.room, ForeignKey(rooms.c[RoomAliases.ID], onupdate="CASCADE", ondelete="NO ACTION"), nullable=False),
    Column(PublicAliases.text, String(128), nullable=False),
    Column(PublicAliases.created_at, DateTime, nullable=False, default=datetime.datetime.now())
)
