"""
FastAPI surface for the CT Flex product slice of AIC.

  GET  /health
  GET  /ct-flex/capabilities
  POST /ct-flex/underwrite          # v2 orchestrator (Income); Health/Life → v1
  POST /ct-flex/underwrite/v1       # legacy ct_flex_product dual-run
  POST /ct-flex/quote               # raw Platform v2 quote JSON
  POST /ct-flex/trip-premium
  POST /ct-flex/portfolio

Run:
  python ct_flex_api.py
  scripts\\serve_ct_flex.bat
"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aic.ct_flex_product import (
    MODEL_VERSION as V1_MODEL_VERSION,
    UnderwritingRequest,
    capabilities as v1_capabilities,
    portfolio_metrics,
    portfolio_to_dict,
    trip_premium,
    underwrite,
    underwrite_to_dict,
)
from aic.orchestrator import PLATFORM_MODEL_VERSION, AICPlatform

ProductCode = Literal["income", "health", "life"]


class UnderwriteBody(BaseModel):
    transactionCount: int = Field(..., ge=0, description="Platform / EcoCash transaction volume")
    product: ProductCode = "income"
    occupation: str = "Courier"
    platform: str = "Bolt"
    nationalId: Optional[str] = None
    fullName: Optional[str] = None
    ecocashConsent: bool = True
    transactions: Optional[List[Any]] = None


class TripBody(BaseModel):
    fareUsd: float = Field(..., gt=0)
    premiumRate: float = Field(..., ge=0)


class PortfolioBody(BaseModel):
    workersEnrolled: int = Field(1247, ge=1)


def _legacy_underwrite(body: UnderwriteBody) -> Dict[str, Any]:
    result = underwrite(
        UnderwritingRequest(
            transaction_count=body.transactionCount,
            product=body.product,
            occupation=body.occupation,
            platform=body.platform,
            national_id=body.nationalId,
            full_name=body.fullName,
            ecocash_consent=body.ecocashConsent,
        )
    )
    return underwrite_to_dict(result)


def _platform_raw(body: UnderwriteBody) -> Dict[str, Any]:
    return {
        "occupation": body.occupation,
        "platform": body.platform,
        "transaction_count": body.transactionCount,
        "product": f"ctflex_{body.product}",
        "ecocash_consent": body.ecocashConsent,
        "national_id": body.nationalId,
        "full_name": body.fullName,
        "transactions": body.transactions,
    }


def create_app(platform: Optional[AICPlatform] = None) -> FastAPI:
    platform = platform or AICPlatform()
    app = FastAPI(
        title="AIC · CT Flex product slice",
        version=PLATFORM_MODEL_VERSION,
        description=(
            "CT Flex actuarial paths. Underwrite (Income) uses Platform v2 orchestrator; "
            "v1 product slice kept at /ct-flex/underwrite/v1 for dual-run."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "service": "aic-ct-flex",
            "modelVersion": PLATFORM_MODEL_VERSION,
            "legacyModelVersion": V1_MODEL_VERSION,
            "underwriteEngine": "aic.orchestrator.AICPlatform",
        }

    @app.get("/ct-flex/capabilities")
    def caps() -> Dict[str, Any]:
        base = v1_capabilities()
        base["modelVersion"] = PLATFORM_MODEL_VERSION
        base["legacyModelVersion"] = V1_MODEL_VERSION
        base["engines"] = {
            "underwrite": "aic.orchestrator.AICPlatform (Income Phase 1)",
            "underwrite_v1": "aic.ct_flex_product",
            "trip_premium": "aic.ct_flex_product",
            "portfolio": "aic.ct_flex_product",
        }
        base["uses"] = [
            "aic.orchestrator → credibility / class-rate risk / decision / explain",
            "engine_model.CredibilityParams (Bühlmann-Straub)",
        ]
        base["note"] = (
            "POST /ct-flex/underwrite uses Platform v2 for Income. "
            "Health/Life still use the v1 product slice. "
            "POST /ct-flex/underwrite/v1 always runs the legacy path. "
            "Add ?dual=1 on underwrite to attach a legacyCompare payload."
        )
        return base

    @app.post("/ct-flex/underwrite")
    def underwrite_endpoint(
        body: UnderwriteBody,
        dual: bool = Query(False, description="Attach legacy v1 result as legacyCompare"),
    ) -> Dict[str, Any]:
        # Phase 1 Income on v2; Health/Life remain on the product slice until rules land
        if body.product != "income":
            try:
                payload = _legacy_underwrite(body)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            payload["enginePath"] = "v1-fallback-non-income"
            return payload

        try:
            payload = platform.underwrite_ctflex_api(_platform_raw(body))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if dual:
            try:
                payload["legacyCompare"] = _legacy_underwrite(body)
            except ValueError:
                payload["legacyCompare"] = None
        return payload

    @app.post("/ct-flex/underwrite/v1")
    def underwrite_v1_endpoint(body: UnderwriteBody) -> Dict[str, Any]:
        try:
            return _legacy_underwrite(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/ct-flex/quote")
    def quote_endpoint(body: UnderwriteBody) -> Dict[str, Any]:
        """Raw Platform v2 quote (not camelCase MVP shape)."""
        try:
            return platform.quote_ctflex(_platform_raw(body))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/ct-flex/trip-premium")
    def trip_endpoint(body: TripBody) -> Dict[str, Any]:
        result = trip_premium(body.fareUsd, body.premiumRate)
        return {
            "fareUsd": result.fare_usd,
            "premiumUsd": result.premium_usd,
            "netUsd": result.net_usd,
            "premiumRate": result.premium_rate,
            "modelVersion": result.model_version,
        }

    @app.post("/ct-flex/portfolio")
    def portfolio_endpoint(body: PortfolioBody) -> Dict[str, Any]:
        return portfolio_to_dict(portfolio_metrics(body.workersEnrolled))

    return app


app = create_app()


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Serve AIC CT Flex product API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    ns = parser.parse_args(argv)
    import uvicorn

    uvicorn.run(app, host=ns.host, port=ns.port)


if __name__ == "__main__":
    main()
