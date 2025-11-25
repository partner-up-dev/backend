"""
author: Lan_zhijiang
date: 2024-08-15
desc: Contract's Display related Schemas
issues: 

references: 

"""

# typing
from app.schemas import BaseSchema
from pydantic import field_serializer, field

from app.schemas.contract import ContractStatus


class ContractSimpleDisplay(BaseSchema):
    id: int = field(alias="_id", serialization_alias="_id")
    status: ContractStatus

    @field_serializer('status')
    def serialize_status(status: ContractStatus) -> str:
        return status.value

