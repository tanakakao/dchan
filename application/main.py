"""FastAPI application for generating optimal experimental designs."""

from fastapi import FastAPI, HTTPException

from functions import OptimalDesign

from .schemas import CandidateRequest, CandidateResponse


app = FastAPI(
    title="D-chan API",
    description="最適実験計画の候補点を生成する API です。",
    version="1.0.0",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return the service health status.

    Returns:
        A mapping containing the service status.
    """
    return {"status": "ok"}


@app.post(
    "/optimal-design/candidate",
    response_model=CandidateResponse,
    tags=["optimal-design"],
)
def create_candidate(request: CandidateRequest) -> CandidateResponse:
    """Generate candidate points for an optimal experimental design.

    Args:
        request: Factor definitions, constraints, and optimization settings.

    Returns:
        Generated candidate points and their correlation matrix.

    Raises:
        HTTPException: If the supplied design conditions cannot be processed.
    """
    optimizer = OptimalDesign()
    try:
        optimizer.set(
            factor_names=request.factor_names,
            x_upper=request.x_upper,
            x_lower=request.x_lower,
            x_step=request.x_step,
            x_levels=request.x_levels,
            mixture_keys=request.mixture_keys,
            sum_target=request.sum_target,
        )
        candidates = optimizer.candidate(
            opt_type=request.opt_type,
            n_iter=request.n_iter,
            n_samples=request.n_samples,
        )
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    correlations = optimizer.df_cor.astype(object).where(
        optimizer.df_cor.notna(), None
    )
    return CandidateResponse(
        candidates=candidates.to_dict(orient="records"),
        correlations=correlations.to_dict(),
    )
