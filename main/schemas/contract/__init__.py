"""
author: Lan_zhijiang
date: 2024/06/10
desc: Contract Module's Schemas
issues:
    #22 #46
docs:
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract
"""

# typing
import typing
from blue_firmament.scheme import BusinessScheme
# from pydantic import field
from enum import Enum
from typing import Dict, List, Annotated

# logger
# from app.libs.logs import top_logger as logging
# logger = logging.getChild("ContractSchema")

# schema
# from app.schemas.partner_request import PartnerRequestContentId

# utils
import time


''' Core Schemas '''
class ContractStatus(Enum):

    """
    :docs
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract#status-%E7%94%9F%E5%91%BD%E5%91%A8%E6%9C%9F
    """

    PENDING = "pending"
    SIGNING = "signing"
    SIGNED = "signed"
    EFFECTING = "effecting"
    CLOSING = "closing"
    CLOSED = "closed"

ContractRef = typing.NewType('ContractRef', int)
# class ContractMetadata(BusinessScheme[ContractRef]):
#
#     """
#     :docs
#     https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract#metadata
#     """
#
#     id: int = field(alias="_id", serialization_alias="_id")
#     created_at: float = field(default_factory=time.time)
#     updated_at: float = field(default_factory=time.time)
#     partner_request: int = field(default=0)
#     status: Annotated[ContractStatus, enum_serializer] = field(default=ContractStatus.PENDING)
#     signature_state: List[str] = field(default_factory=list, description="reference to Account")
#
# class ContractContent(BaseSchema):
#
#     """
#     :docs: \n
#     https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract#content
#     """
#
#     clauses: Dict[PartnerRequestContentId, int] = field(default_factory=dict, description="PRContentId Mapping to Clause")
#
#     def deref(self, deref_fields: List[str] = ["clauses"]) -> dict:
#
#         """
#         :desc
#             clauses Dict[PRContentId, clause_id] -> Dict[PRContentId, Clause]
#         """
#
#         derefed_result = {}
#
#         for field in deref_fields:
#             derefed_field = None
#             if field == "clauses":
#                derefed_field = []
#                for content_id, clause_id in self.clauses.items():
#                    try:
#                        # derefed_field.append(ClauseManager(clause_id).schema)
#                        # TODO
#                        pass
#                    except Exception as e:
#                        logger.error(f"Failed to deref clause {clause_id}. {e}")
#                        continue
#             else:
#                 continue
#
#             derefed_result[field] = derefed_field
#
#         return derefed_result
#
# class Contract(ContractMetadata, ContractContent):
#     pass
