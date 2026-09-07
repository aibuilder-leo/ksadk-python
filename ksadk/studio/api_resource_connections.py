"""Data-only resource connection configuration under the existing Studio API guard."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, Query
from pydantic import Field

from ksadk.plugins.contracts import PluginContractModel
from ksadk.studio.errors import StudioError
from ksadk.studio.resource_connections import ResourceConnectionDeclaration


class SaveResourceConnection(PluginContractModel):
    expected_revision: int = Field(strict=True, ge=0)
    connection: ResourceConnectionDeclaration


class ValidateResourceBindings(PluginContractModel):
    expected_revision: int = Field(strict=True, ge=1)


def register_resource_connection_routes(app: FastAPI, studio: Any) -> None:
    @app.get("/api/v1/agents/{agent_id}/resource-bindings/status")
    async def binding_status(
        agent_id: str,
        activation_id: str = Query(alias="activationId", min_length=1, max_length=256),
    ):
        return await studio.resource_binding_status(agent_id, activation_id=activation_id)

    @app.post("/api/v1/agents/{agent_id}/resource-bindings/validate")
    async def validate_bindings(agent_id: str, request: ValidateResourceBindings):
        return await asyncio.to_thread(
            studio.validate_resource_bindings,
            agent_id,
            expected_revision=request.expected_revision,
        )

    @app.get("/api/v1/resource-connections")
    async def list_connections():
        records = await asyncio.to_thread(studio.resource_connections.list)
        return {
            "items": [
                {**record.model_dump(by_alias=True, mode="json"), "validationState": "unverified"}
                for record in records
            ]
        }

    @app.put("/api/v1/resource-connections/{connection_ref:path}")
    async def save_connection(connection_ref: str, request: SaveResourceConnection):
        if request.connection.target.connection_ref != connection_ref:
            raise StudioError(
                "RESOURCE_CONNECTION_REFERENCE_MISMATCH",
                "路径与连接引用不一致",
                status_code=422,
            )
        record = await asyncio.to_thread(
            studio.resource_connections.save,
            request.connection,
            expected_revision=request.expected_revision,
        )
        return {**record.model_dump(by_alias=True, mode="json"), "validationState": "unverified"}
