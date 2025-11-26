"""
author: Lan_zhijiang
date: 2024/06/07
desc: Requirement's Schema, a sub schema of Partner Request
issues:
    #21 http://git.hadream.ltd/anana/backend/main/-/work_items/21#note_2152
references:
    https://app.apifox.com/link/project/4406548/apis/schema-95444957
"""

from typing import List, Tuple
from pydantic import BaseModel
from enum import Enum
from utils import encryption as Encryption


class RequirementType(Enum):
    TAG = "tag"


RequirementTagContent = str  # label _id
RequirementContent = RequirementTagContent | None


class Requirement(BaseModel):
    """Requirement model."""
    id: str | None = None
    type: RequirementType | None = None
    content: RequirementContent = None
    popularity: float = 0.0

    def __str__(self) -> str:
        try:
            return "%s%s" % (self.type, self.content)
        except AttributeError:
            return ""

    def compute_id(self):
        """Set the _id"""
        self.id = Encryption.md5(str(self))


RequirementRef = str


class Requirements(BaseModel):
    """Requirements collection model."""
    root: List[Tuple[float, RequirementRef]]


RequirementsDefault = lambda: Requirements(root=[])

RequirementsDetail = List[Tuple[float, Requirement]]
RequirementsDetailDefault = []
