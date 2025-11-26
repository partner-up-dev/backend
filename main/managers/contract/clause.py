"""
author: Lan_zhijiang
date: 2024-08-16
desc: Contract/Clause Manager
issues: 
    #47
references: 

"""

# typing
from app.managers import BaseManager
from typing import List

# logger
from app.libs.logs import top_logger as logging
logger = logging.getChild("ClauseManager")

# schemas
from app.schemas.contract.clause import Clause

# db
from app.libs.postgresql import supabase_serv_db


class ClauseManager(BaseManager):

    _table = "clause"

    def __init__(self, clause_id: int | None = None, **data) -> None:

        if clause_id:
            data = self.fetch_data_by_id(clause_id)

        self._schema = Clause(**data)

    @property
    def schema(self) -> Clause:
        return self._schema

    @classmethod
    def fetch_data_by_id(cls, clause_id: int, *fields) -> dict:

        logger.info("Fetch clause's %s by _id %s", fields, clause_id)

        fetch_result = supabase_serv_db.fetch(cls._table, columns=fields, filters=[("eq", ("_id", clause_id))], logger=logger)
        return fetch_result[0]
    
    @classmethod
    def bulk_create(cls, clauses: List[Clause]) -> List['ClauseManager']:

        logger.info("Directly bulk create clauses to database")

        clauses = [clause.json(exclude_fields=['id']) for clause in clauses]
        insert_result: List[dict]  = supabase_serv_db.insert(
            cls._table, clauses, logger=logger
        )

        return [cls(**clause) for clause in insert_result]
    
    @classmethod
    def create(cls, clause: Clause) -> 'ClauseManager':

        logger.info("Create clause %s", clause)

        to_insert = clause.json(exclude_fields=['id']);
        insert_result = supabase_serv_db.insert(
            cls._table, to_insert, logger=logger
        )

        return cls(**insert_result)
    
    def set_performers(self, performers: List[str]) -> None:

        logger.info("Set clause's performers to %s", performers)

        self._schema.performers = performers

