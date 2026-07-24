"""
FastAPI surface for the CT Flex product slice of AIC.

  GET  /health
  GET  /ct-flex/capabilities
  POST /ct-flex/underwrite
  POST /ct-flex/trip-premium
  POST /ct-flex/portfolio

Run:
  python ct_flex_api.py
  serve_ct_flex.bat
"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ct_flex_product import (
    MODEL_VERSION,
    UnderwritingRequest,
    capabilities,
    portfolio_metrics,
    portfolio_to_dict,
    trip_premium,
    underwrite,
    underwrite_to_dict,
)

ProductCode = Literal["income", "health", "life"]


class UnderwriteBody(BaseModel):
    transactionCount: int = Field(..., ge=0, description="Platform / EcoCash transaction volume")
    product: ProductCode = "income"
    occupation: str = "Courier"
    platform: str = "Bolt"
    nationalId: Optional[str] = None
    fullName: Optional[str] = None
    ecocashConsent: bool = True


class TripBody(BaseModel):
    fareUsd: float = Field(..., gt=0)
    premiumRate: float = Field(..., ge=0)


class PortfolioBody(BaseModel):
    workersEnrolled: int = Field(1247, ge=1)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIC · CT Flex product slice",
        version=MODEL_VERSION,
        description=(
            "Exposes only the actuarial paths CT Flex needs. "
            "Core math comes from AIC engine_model; other AIC APIs remain separate."
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
            "modelVersion": MODEL_VERSION,
        }

    @app.get("/ct-flex/capabilities")
    def caps() -> Dict[str, Any]:
        return capabilities()

    @app.post("/ct-flex/underwrite")
    def underwrite_endpoint(body: UnderwriteBody) -> Dict[str, Any]:
        try:
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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return underwrite_to_dict(result)

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
