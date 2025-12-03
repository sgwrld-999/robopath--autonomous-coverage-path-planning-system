from typing import List, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


# -----------------------------
# Wall & Obstacles (Inputs)
# -----------------------------

class WallDimensions(BaseModel):
    """Represents the dimensions of the wall to be covered."""

    width: float = Field(..., description="Width of the wall in meters.")
    height: float = Field(..., description="Height of the wall in meters.")


class Obstacle(BaseModel):
    """Represents an obstacle on the wall defined by its bottom-left coordinate and size."""

    x: float = Field(..., description="X-coordinate of the obstacle's bottom-left corner.")
    y: float = Field(..., description="Y-coordinate of the obstacle's bottom-left corner.")
    width: float = Field(..., description="Width of the obstacle in meters.")
    height: float = Field(..., description="Height of the obstacle in meters.")


# -----------------------------
# Planner Parameters (Detailed)
# -----------------------------

class PlannerParameters(BaseModel):
    """Parameters used by the coverage planner algorithm."""

    tool_width: float = Field(..., description="Width of the brush/nozzle used for wall finishing.")
    overlap: float = Field(..., description="Fractional overlap between consecutive lanes (0 to 0.5).")
    safe_margin: float = Field(..., description="Safety inflation applied around obstacles.")
    orientation: Literal["auto", "vertical", "horizontal"] = Field(
        "auto",
        description="Lane sweep orientation: auto-selected or forced vertical/horizontal.",
    )
    waypoint_spacing: Optional[float] = Field(
        None,
        description="Spacing between generated waypoints. Defaults to tool_width/2 if omitted."
    )
    min_segment_length: Optional[float] = Field(
        None,
        description="Minimum length of a segment to be considered valid during lane clipping."
    )


# -----------------------------
# Path Inputs (Full Request)
# -----------------------------

class PathRequest(BaseModel):
    """
    Represents the full request body received from the API
    to generate a coverage path/trajectory.
    """

    job_name: Optional[str] = Field(
        None,
        description="Optional human-friendly name for the planning job."
    )
    wall: WallDimensions = Field(..., description="Dimensions of the wall to be covered.")
    obstacles: List[Obstacle] = Field(
        default_factory=list,
        description="List of obstacles present on the wall."
    )
    planner_params: PlannerParameters = Field(
        ..., description="Planner configuration for path generation."
    )


# -----------------------------
# Waypoints & Planner Output
# -----------------------------

class Waypoint(BaseModel):
    """Represents a single waypoint along the robot's generated coverage path."""

    seq: int = Field(..., description="Sequence number of the waypoint.")
    x: float = Field(..., description="X-coordinate of the waypoint.")
    y: float = Field(..., description="Y-coordinate of the waypoint.")
    theta: float = Field(..., description="Heading angle (radians).")
    speed: Optional[float] = Field(
        None,
        description="Optional speed of the robot at this waypoint."
    )


class ForbiddenRect(BaseModel):
    """Represents an inflated & merged forbidden rectangle used during planning."""

    x: float = Field(..., description="X-coordinate of forbidden rectangle after inflation.")
    y: float = Field(..., description="Y-coordinate of forbidden rectangle after inflation.")
    width: float = Field(..., description="Width of forbidden region.")
    height: float = Field(..., description="Height of forbidden region.")


# -----------------------------
# Planner Metadata (Output)
# -----------------------------

class PlannerMetadata(BaseModel):
    """Planner metadata capturing useful computation information."""

    path_length_m: float = Field(..., description="Total path length in meters.")
    coverage_fraction: float = Field(
        ..., description="Fraction (0..1) of the wall covered by the robot."
    )
    num_waypoints: int = Field(..., description="Total number of generated waypoints.")
    planner_version: str = Field(
        ..., description="Version identifier for the planner logic."
    )
    validation_warnings: Optional[List[str]] = Field(
        None,
        description="Any validation warnings generated during planning."
    )
    collision_flag: bool = Field(
        ..., description="Indicates if any potential collisions were detected."
    )


# -----------------------------
# Final API Response
# -----------------------------

class TrajectoryResponse(BaseModel):
    """
    Response returned after generating a coverage trajectory.
    Contains full path, metadata, wall details, and processed obstacles.
    """

    id: int = Field(..., description="Unique trajectory identifier.")
    created_at: datetime = Field(
        ..., description="Timestamp when the trajectory was created."
    )
    job_name: Optional[str] = Field(
        None, description="User-friendly name assigned to the job."
    )

    # Inputs
    wall: WallDimensions = Field(..., description="Original wall dimensions.")
    obstacles: List[Obstacle] = Field(
        ..., description="Original obstacles as provided by the user."
    )
    planner_params: PlannerParameters = Field(
        ..., description="Planner configuration used for this trajectory."
    )

    # Processed
    forbidden_rects: List[ForbiddenRect] = Field(
        ..., description="List of inflated & merged forbidden regions."
    )

    # Output path
    waypoints: List[Waypoint] = Field(..., description="Generated list of waypoints.")

    # Metadata
    meta: PlannerMetadata = Field(..., description="Computed metadata of the trajectory.")

    model_config = ConfigDict(from_attributes=True)
