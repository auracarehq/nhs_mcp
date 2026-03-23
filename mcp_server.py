"""
MCP server exposing clinical knowledge tools over SSE transport.

Mount at /mcp in main.py. Clients connect via:
  GET  /mcp/sse           — open SSE stream
  POST /mcp/messages/     — send JSON-RPC messages

Compatible with Claude Desktop, Claude Code, and any MCP-capable client.
"""

from __future__ import annotations

import json
import os

import db
from domains.dmd.service import get_or_fetch as dmd_get_or_fetch
from domains.dmd.service import search as dmd_search
from domains.icd.service import get_or_fetch as icd_get_or_fetch
from domains.icd.service import search as icd_search
from domains.open_prescribing.service import search as op_search_bnf
from domains.open_prescribing.service import spending as op_spending
from domains.open_prescribing.service import spending_by_org as op_spending_by_org
from domains.snomed.service import get_or_fetch as snomed_get_or_fetch
from domains.snomed.service import search as snomed_search
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "NHS Clinical Knowledge",
    instructions=(
        "Tools for UK clinical knowledge. Use these to look up drugs, conditions, "
        "clinical terminology codes (SNOMED CT, ICD-11), prescribing analytics, "
        "and NHS/NICE/MHRA guidance. All sources are official UK/WHO references."
    ),
    # Disable DNS rebinding protection — this server is public-facing over HTTPS,
    # so the Azure ingress handles security; localhost-only validation would block clients.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
async def search_clinical_content(query: str) -> list[dict]:
    """Search scraped NHS, NICE, and MHRA content by name.

    Searches: NHS Health A-Z (conditions, symptoms, medicines, treatments),
    NICE Clinical Knowledge Summaries, BNF, BNFc, and MHRA Drug Safety Updates.
    Returns slug, name, and source domain. Use the slug to retrieve full content
    via the REST API if needed.
    """
    rows = await db.search_pages(None, query)
    return [{"slug": r["slug"], "name": r["name"], "source": r["domain"]} for r in rows]


@mcp.tool()
async def search_snomed(query: str, limit: int = 10) -> dict:
    """Search SNOMED CT UK Clinical Edition for clinical concepts.

    Returns concept IDs, preferred terms, FSNs (fully specified names), and
    hierarchy classifications (disorder, finding, substance, product, etc.).
    Use concept_id with get_snomed_concept() to retrieve and cache full detail.
    """
    result = await snomed_search(query, limit)
    return result.model_dump()


@mcp.tool()
async def get_snomed_concept(concept_id: str) -> dict:
    """Fetch full detail for a SNOMED CT concept by ID.

    Returns preferred term, FSN, hierarchy, active status, and raw JSON.
    Caches locally on first fetch — subsequent calls are instant.
    """
    detail = await snomed_get_or_fetch(concept_id)
    return detail.model_dump()


@mcp.tool()
async def search_icd11(query: str) -> dict:
    """Search ICD-11 (WHO disease classification) by clinical term.

    Returns ICD-11 codes (e.g. '5A10'), entity IDs, and titles.
    Use entity_id with get_icd11_concept() for full detail including definition.
    Returns an error message if ICD-11 credentials are not configured on the server.
    """
    if not os.environ.get("ICD_CLIENT_ID"):
        return {"error": "ICD-11 credentials not configured on this server instance"}
    result = await icd_search(query)
    return result.model_dump()


@mcp.tool()
async def get_icd11_concept(entity_id: str) -> dict:
    """Fetch full detail for an ICD-11 concept by WHO entity ID.

    entity_id is the numeric suffix of the WHO URI (e.g. '1630407678' from
    'https://id.who.int/icd/entity/1630407678'). Returns ICD code, title,
    clinical definition, and raw JSON. Caches locally.
    """
    if not os.environ.get("ICD_CLIENT_ID"):
        return {"error": "ICD-11 credentials not configured on this server instance"}
    detail = await icd_get_or_fetch(entity_id)
    return detail.model_dump()


@mcp.tool()
async def search_dmd(query: str, limit: int = 10) -> dict:
    """Search dm+d (NHS Dictionary of Medicines and Devices) by drug or device name.

    dm+d codes are SNOMED CT UK Drug Extension codes. Results include the dm+d ID,
    display name, and concept type (VTM, VMP, AMP, VMPP, AMPP).
    Use dmd_id with get_dmd_product() for BNF code and full FHIR detail.
    """
    result = await dmd_search(query, limit)
    return result.model_dump()


@mcp.tool()
async def get_dmd_product(dmd_id: str) -> dict:
    """Fetch full detail for a dm+d product by its SNOMED/dm+d code.

    Returns name, concept type, BNF code (if available), and raw FHIR Parameters
    payload from the NHS Terminology Server. Caches locally.
    """
    detail = await dmd_get_or_fetch(dmd_id)
    return detail.model_dump()


@mcp.tool()
async def search_bnf(query: str) -> dict:
    """Search BNF (British National Formulary) codes by drug name.

    Returns BNF codes, drug names, linked dm+d IDs, and a generic flag.
    BNF codes can be used with get_bnf_spending() for prescribing analytics.
    """
    result = await op_search_bnf(query)
    return result.model_dump()


@mcp.tool()
async def get_bnf_spending(bnf_code: str) -> dict:
    """Get national NHS prescribing spending data for a BNF code.

    Returns monthly time-series data: actual cost, net cost, quantity dispensed,
    and total items. Sourced from OpenPrescribing (openprescribing.net); updated monthly.
    Useful for understanding prescribing volume and cost trends.
    """
    result = await op_spending(bnf_code)
    return result.model_dump()


@mcp.tool()
async def get_bnf_spending_by_org(bnf_code: str, org_type: str = "practice") -> dict:
    """Get NHS prescribing spending for a BNF code broken down by organisation.

    org_type options: 'practice', 'ccg', 'pcn', 'sicbl', 'regional_team'.
    Returns spending per organisation per month — useful for identifying variation
    in prescribing patterns across GP practices or ICBs.
    """
    result = await op_spending_by_org(bnf_code, org_type)
    return result.model_dump()
