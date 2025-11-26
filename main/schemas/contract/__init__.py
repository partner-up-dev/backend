"""
author: Lan_zhijiang
date: 2024/06/10
desc: Contract Module's Schemas
issues:
    #22 #46
docs:
    https://git.hadream.ltd/anana/gitlab-profile/-/wikis/Design/Contract
"""

import typing
from enum import Enum


class ContractStatus(Enum):
    """Contract status enumeration."""

    PENDING = "pending"
    SIGNING = "signing"
    SIGNED = "signed"
    EFFECTING = "effecting"
    CLOSING = "closing"
    CLOSED = "closed"


ContractRef = typing.NewType('ContractRef', int)
