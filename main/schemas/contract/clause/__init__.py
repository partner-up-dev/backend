"""
author: Lan_zhijiang
date: 2024-08-15
desc: Contract/Clause's Schemas
issues: 
    #46
docs: 
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract/Clause
"""

__module_name__ = "ClauseSchema"

# logger
from app.libs.logs import top_logger as logging
logger = logging.getChild(__module_name__)

# typing
from app.schemas import BaseSchema, enum_serializer, TranslatableEnum
from enum import Enum
from typing import Annotated, List, Dict, Union
from pydantic import field

# i18n
from app.libs import i18n
t = i18n.get_translator(__module_name__)
def de_p(context: str, message: str) -> str: 
    return message

# schemas
from app.schemas.base import Getter, RowReference


''' Obligation '''
class ObligationContentType(Enum):

    PLAIN = "plain"
    ROW_REFERENCE = "row_reference"
    GETTER = "getter"  # TODO 在manager创建对应的mapper
    DIRECT = "direct"

class ObligationGetter(TranslatableEnum):
    def __init__(self, *args):
        super().__init__(t, context="obligation_getter")

    RIDE_HAILING_ROUTE = de_p("obligation_getter", "ride_hailing_route")

class Obligation(BaseSchema):

    """
    :docs
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract/Clause#obligation
    """

    content_type: Annotated[ObligationContentType, enum_serializer]
    content: Union[
        str, # plain
        dict, # direct
        RowReference, # row_reference
        Getter # getter
    ]


''' Default '''
class EnforcerType(Enum):

    MANUAL = "manual"
    AUTOMATIC = "automatic"

class Enforcer(Enum):
    def __init_subclass__(cls) -> None:
        cls._translator = t

    BLOCK = de_p("enforcer", "block")

class DefaultBranch(BaseSchema):

    """
    docs:
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract/Clause#default
    """
    
    enforcer: Annotated[Enforcer, enum_serializer] # TODO 在manager创建对应的mapper
    enforcer_type: Annotated[EnforcerType, enum_serializer]


''' Validation '''

class Validator(Enum):    
    def __init_subclass__(cls) -> None:
        cls._translator = t

    RIDE_HAILING_ROUTE = de_p("validator", "ride_hailing_route")

class ValidateAt(Enum):

    def __init_subclass__(cls) -> None:
        cls._translator = t

    ON_PROSECUTED = de_p("validate_at", "on_prosecuted")

class Validation(BaseSchema):

    """
    :docs
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract/Clause#validation
    """

    validator: Annotated[Validator, enum_serializer] # TODO 在manager创建对应的mapper
    validate_at: Annotated[ValidateAt, enum_serializer] # TODO 在manager创建对应的mapper
    result: str | None = None


''' Core Schemas '''
class ClauseStatus(Enum):

    PENDING = "pending"
    PERFORMING = "performing"
    VALIDATING = "validating"
    PENALIZING = "penalizing"
    CLOSED = "closed"

class ClauseMetadata(BaseSchema):

    """
    :docs
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract/Clause#metadata
    """

    id: int = field(alias="_id", serialization_alias="_id")
    template_id: int
    status: Annotated[ClauseStatus, enum_serializer] = field(default=ClauseStatus.PENDING)
    performers: List[str] = field(default_factory=list, description="reference to Account")

class ClauseContent(BaseSchema):

    """
    :docs
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract/Clause#content
    """

    obligation: Obligation | None
    default: Dict[str, DefaultBranch] = field(default_factory=dict)
    validation: Validation | None

class Clause(ClauseMetadata, ClauseContent):
    pass
