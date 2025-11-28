"""Communication App Routes.

Business logic endpoints for chats and messages.
Simple CRUD operations (get, create, put, delete, upsert) are handled by direct
database access from the client.
"""

import fastapi
from typing import Optional as Opt
from fastapi import Depends, HTTPException

from core.auth import AuthInfo, require_auth
from core.engine import get_db_session
import sqlmodel

from .schemas.chat import Chat, ChatRef, ChatType
from .schemas.message import Message, MessageRef, MessageType

router = fastapi.APIRouter()


@router.get("/chat/{chat_id}/messages")
def get_chat_messages(
    chat_id: ChatRef,
    start: int = 0,
    offset: int = 6,
    desc: bool = True,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> list[Message]:
    """Get messages from a chat.

    Supports pagination and ordering.
    Requires authentication.
    """
    chat = db.get(Chat, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    statement = sqlmodel.select(Message).where(Message.chat == chat_id)
    if desc:
        statement = statement.order_by(Message.id.desc())
    else:
        statement = statement.order_by(Message.id)
    statement = statement.offset(start).limit(offset)

    messages = db.exec(statement).all()
    return list(messages)


@router.get("/chat/mine")
def get_my_chats(
    chat_type: Opt[ChatType] = None,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> list[ChatRef]:
    """Get chats for current user.

    Optionally filter by chat type.
    """
    statement = sqlmodel.select(Chat.id).where(Chat.created_by == auth.user_id)
    if chat_type:
        statement = statement.where(Chat.type == chat_type.value)
    results = db.exec(statement).all()
    return list(results)


@router.post("/chat/message/plain")
def send_plain_message(
    to_chat: ChatRef,
    content: str,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> Message:
    """Send a plain text message to a chat.

    Creates a new message with PLAIN type.
    """
    chat = db.get(Chat, to_chat)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    message = Message(
        chat=to_chat,
        created_by=auth.user_id,
        type=MessageType.PLAIN.value,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.put("/chat/message/{message_id}/viewed")
def mark_message_viewed(
    message_id: MessageRef,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> Message:
    """Mark a message as viewed by the current user.

    Adds the user to the viewed list if not already present.
    """
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    import json
    viewed = json.loads(message.viewed) if message.viewed else []
    if auth.user_id not in viewed:
        viewed.append(auth.user_id)
        message.viewed = json.dumps(viewed)
        db.add(message)
        db.commit()
        db.refresh(message)

    return message
