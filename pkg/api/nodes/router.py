from fastapi import APIRouter
from fastapi.responses import JSONResponse

from pkg.api.schemas import NodesResponse
from pkg.src.mongodb import AsyncBlockchainDB


class NodesRouter:
    def __init__(self, db: AsyncBlockchainDB):
        self.router = APIRouter()
        self.router.add_api_route(
            "",
            self.get_nodes,
            methods=["GET"],
            response_model=NodesResponse,
            summary="Get Nodes"
        )

        self.db: AsyncBlockchainDB = db

    async def get_nodes(self):
        """
        Get list of active nodes on chain.

        Returns:
        - **NodesResponse**: List of active nodes.
        """
        nodes = await self.db.get_all_nodes()
        return JSONResponse(content=NodesResponse(data=nodes).dict())
