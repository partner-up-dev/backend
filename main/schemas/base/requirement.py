"""
author: Lan_zhijiang
date: 2024/06/07
desc: Requirement's Schema, a sub schema of Partner Request
issues: 
    #21 http://git.hadream.ltd/anana/backend/main/-/work_items/21#note_2152
references:
    https://app.apifox.com/link/project/4406548/apis/schema-95444957
"""

from interface_common.schemas.business import BaseSchema
from typing import Union, List, Tuple
from pydantic import RootModel, field, field_serializer
from enum import Enum

# exception
from interface_common.libs.exceptions import NotFound

# util
from interface_common.utils import encryption as Encryption

# supabase

class RequirementType(Enum):
    TAG = "tag"

RequirementTagContent = str  # label _id
RequirementContent = Union[RequirementTagContent, None]


class Requirement(BaseSchema[str]):

    def __str__(self) -> str:

        # WARNING the type might be enum type, need .value
        #   but currently, no request to set requirement, so no enum type here
        try:
            return "%s%s" % (self.type, self.content)
        except AttributeError:
            return ""
        
    def compute_id(self):
        
        """
        Set the _id
        """
        self.id = Encryption.md5(str(self))

    def set_content(self, content: RequirementContent):
        self._content = content
        self.compute_id()

    def get_content(self):
        return self._content
    
    def set_type(self, type: RequirementType):
        self._type = type
        self.compute_id()

    def get_type(self):
        return self._type

    _ID_TYPE = "hash"
    popularity: float

    type: RequirementType = property(
        get_type, set_type
    )
    content: RequirementContent = property(
        get_content, set_content
    )


RequirementRef = str

class Requirements(RootModel):
    root: List [
        Tuple [
            float,  # weight
            RequirementRef  # requirement _id
        ]
    ]
RequirementsDefault = lambda: Requirements(root=[])

RequirementsDetail = List[
    Tuple[
        float,  # weight
        Requirement
    ]
]
RequirementsDetailDefault = []
