"""Request and response schemas for the optimal-design API."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, root_validator


class CandidateRequest(BaseModel):
    """Input parameters used to generate an optimal design."""

    factor_names: List[str] = Field(..., min_items=1)
    x_upper: List[Optional[float]]
    x_lower: List[Optional[float]]
    x_step: List[Optional[float]]
    x_levels: List[Optional[List[Any]]]
    mixture_keys: Optional[Union[List[str], List[List[str]]]] = None
    sum_target: Optional[Union[float, List[float]]] = None
    opt_type: Literal["D", "A", "E", "I", "minmax"] = "D"
    n_iter: int = Field(200, ge=1)
    n_samples: int = Field(30, ge=1)

    @root_validator(skip_on_failure=True)
    def validate_factor_lists(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that every factor has one definition in each input list.

        Args:
            values: Values parsed by Pydantic.

        Returns:
            The validated values.

        Raises:
            ValueError: If list lengths, factor names, or factor settings are invalid.
        """
        factor_names = values.get("factor_names") or []
        if len(set(factor_names)) != len(factor_names):
            raise ValueError("factor_names must not contain duplicates")

        list_fields = ("x_upper", "x_lower", "x_step", "x_levels")
        for field_name in list_fields:
            items = values.get(field_name)
            if items is not None and len(items) != len(factor_names):
                raise ValueError(
                    f"{field_name} must have the same length as factor_names"
                )

        for index, levels in enumerate(values.get("x_levels") or []):
            if levels is not None:
                if not levels:
                    raise ValueError("categorical factor levels must not be empty")
                continue
            numeric_values = (
                values["x_lower"][index],
                values["x_upper"][index],
                values["x_step"][index],
            )
            if any(value is None for value in numeric_values):
                raise ValueError("numeric factors require lower, upper, and step values")
            lower, upper, step = numeric_values
            if lower > upper:
                raise ValueError("x_lower must be less than or equal to x_upper")
            if step <= 0:
                raise ValueError("x_step must be greater than zero")
        return values


class CandidateResponse(BaseModel):
    """Generated design candidates and their correlation matrix."""

    candidates: List[Dict[str, Any]]
    correlations: Dict[str, Dict[str, Optional[float]]]
