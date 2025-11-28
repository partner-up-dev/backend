"""Communication App Routes.

Exposes business logic from managers as FastAPI endpoints.
Routes handle HTTP concerns (validation, status codes, responses).
Managers handle business logic and database operations.
"""

import fastapi
from typing import Optional as Opt
from fastapi import Depends, HTTPException, status

from core.auth import AuthInfo, require_auth

from .managers import ChatManager, MessageManager
from .schemas.chat import Chat, ChatRef, ChatType
from .schemas.message import Message, MessageRef

router = fastapi.APIRouter()


@router.get("/chat/{chat_id}/messages")
def get_chat_messages(
    chat_id: ChatRef,
    start: int = 0,
    offset: int = 6,
    desc: bool = True,
    auth: AuthInfo = Depends(require_auth),
) -> list[Message]:
    """Get messages from a chat.

    Supports pagination and ordering.
    Requires authentication.
    """
    chat = ChatManager.get(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    return MessageManager.get_chat_messages(
        chat_id=chat_id,
        start=start,
        offset=offset,
        desc=desc,
    )


@router.get("/chat/mine")
def get_my_chats(
    chat_type: Opt[ChatType] = None,
    auth: AuthInfo = Depends(require_auth),
) -> list[ChatRef]:
    """Get chats for current user.

    Optionally filter by chat type.
    """
    return ChatManager.get_user_chats(
        user_id=auth.user_id,
        chat_type=chat_type,
    )


@router.post("/chat/message/plain", status_code=status.HTTP_201_CREATED)
def send_plain_message(
    to_chat: ChatRef,
    content: str,
    auth: AuthInfo = Depends(require_auth),
) -> Message:
    """Send a plain text message to a chat.

    Creates a new message with PLAIN type.
    """
    chat = ChatManager.get(to_chat)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    return MessageManager.send_plain_message(
        chat_id=to_chat,
        created_by=auth.user_id,
        content=content,
    )


@router.put("/chat/message/{message_id}/viewed")
def mark_message_viewed(
    message_id: MessageRef,
    auth: AuthInfo = Depends(require_auth),
) -> Message:
    """Mark a message as viewed by the current user.

    Adds the user to the viewed list if not already present.
    """
    message = MessageManager.mark_as_viewed(
        message_id=message_id,
        user_id=auth.user_id,
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    return message


@router.put("/chat/direct_message/{to_id}", status_code=status.HTTP_200_OK)
def create_dm_chat(
    to_id: str,
    auth: AuthInfo = Depends(require_auth),
    response: fastapi.Response = None,
) -> Chat:
    """Create or get a direct message chat.

    If a DM chat already exists between the users, returns it.
    Otherwise creates a new one.
    """
    try:
        chat, created = ChatManager.create_dm_chat(
            from_id=auth.user_id,
            to_id=to_id,
        )
        if created:
            response.status_code = status.HTTP_201_CREATED
        return chat
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
