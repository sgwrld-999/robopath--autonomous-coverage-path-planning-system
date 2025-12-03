"""
API router for trajectory planning.

Provides endpoints to:
- create a new trajectory (runs the planner synchronously)
- list trajectories (basic pagination)
- fetch a single trajectory by id

This router uses:
- Pydantic request/response models (schema.py)
- SQLAlchemy ORM (database.py)
- Planner implementation (wall_done_planner.py)

All code follows PEP8 and dependency-injection patterns used by FastAPI.
"""


from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src import database
from src.database import TrajectoryDB, Base, engine, get_db
from src.wall_done_planner import plan_coverage
from src.schema import (
    PathRequest,
    TrajectoryResponse,
    Waypoint,
    ForbiddenRect,
    PlannerMetadata,
)

# Ensure DB tables exist (creates SQLite file and tables on first import)
Base.metadata.create_all(bind=engine)

# API Router
router = APIRouter(prefix="/api/trajectories", tags=["trajectories"])


# -------------------------
# Helpers
# -------------------------

def _db_to_trajectory_response(db_obj: TrajectoryDB) -> TrajectoryResponse:
    """
    Convert a TrajectoryDB row into a TrajectoryResponse Pydantic model.
    """
    waypoints_data = db_obj.waypoints or []
    forbidden_data = db_obj.forbidden_rects or []
    meta_data = db_obj.meta or {}

    # Convert to Pydantic-friendly types
    waypoints = [
        Waypoint(
            seq=int(p.get("seq", i + 1)),
            x=float(p["x"]),
            y=float(p["y"]),
            theta=float(p.get("theta", 0.0)),
            speed=p.get("speed"),
        )
        for i, p in enumerate(waypoints_data)
    ]

    forbidden_rects = [
        ForbiddenRect(
            x=float(r["x"]), y=float(r["y"]), width=float(r["w"]), height=float(r["h"])
        )
        for r in forbidden_data
    ]

    meta = PlannerMetadata(
        path_length_m=float(meta_data.get("path_length", 0.0)),
        coverage_fraction=float(meta_data.get("coverage_fraction", 0.0)),
        num_waypoints=int(meta_data.get("num_waypoints", len(waypoints))),
        planner_version=str(meta_data.get("planner_version", "v1")),
        validation_warnings=meta_data.get("validation_warnings") or None,
        collision_flag=bool(meta_data.get("collision_flag", False)),
    )

    response = TrajectoryResponse(
        id=int(db_obj.id),
        created_at=db_obj.created_at,
        job_name=db_obj.job_name,
        wall={"width": db_obj.wall_width, "height": db_obj.wall_height},
        obstacles=db_obj.obstacles or [],
        planner_params=db_obj.planner_params or {},
        forbidden_rects=forbidden_rects,
        waypoints=waypoints,
        meta=meta,
    )
    return response


# -------------------------
# Routes
# -------------------------

@router.post(
    "/",
    response_model=TrajectoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trajectory and run planner",
)
def create_trajectory(
    request: PathRequest,
    db: Session = Depends(get_db),
) -> TrajectoryResponse:
    """
    Create a new trajectory record, run the planner with provided parameters,
    persist the result, and return the generated trajectory.
    """
    # Validate basic inputs (Pydantic handles most validation)
    params = request.planner_params
    wall = request.wall
    obstacles = request.obstacles or []

    try:
        # Run planner (synchronous). Planner returns dict with waypoints, meta, etc.
        planner_result = plan_coverage(
            wall_w=wall.width,
            wall_h=wall.height,
            obstacles=[{"x": o.x, "y": o.y, "w": o.width, "h": o.height} for o in obstacles],
            tool_w=params.tool_width,
            overlap=params.overlap,
            safe_margin=params.safe_margin,
            waypoint_spacing=params.waypoint_spacing,
            orientation=params.orientation,
            min_segment_length=params.min_segment_length,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - unexpected planner failure
        raise HTTPException(
            status_code=500, detail=f"Planner failed: {str(exc)}"
        )

    # If planner returned an error dict (collision), return 400 with details
    if isinstance(planner_result, dict) and planner_result.get("error"):
        raise HTTPException(
            status_code=400,
            detail={"planner_error": planner_result.get("error"), "info": planner_result.get("collisions")},
        )

    # Prepare DB record
    db_obj = TrajectoryDB(
        job_name=request.job_name,
        wall_width=wall.width,
        wall_height=wall.height,
        obstacles=[{"x": o.x, "y": o.y, "width": o.width, "height": o.height} for o in obstacles],
        planner_params=params.model_dump() if hasattr(params, "model_dump") else params.dict(),
        forbidden_rects=planner_result.get("forbidden_rects", []),
        waypoints=[
            {
                "seq": idx + 1,
                "x": float(p["x"]),
                "y": float(p["y"]),
                "theta": float(p.get("theta", 0.0)),
                "speed": p.get("speed"),
            }
            for idx, p in enumerate(planner_result.get("waypoints", []))
        ],
        meta={
            "path_length": planner_result.get("meta", {}).get("path_length"),
            "coverage_fraction": planner_result.get("meta", {}).get("coverage_fraction"),
            "num_waypoints": planner_result.get("meta", {}).get("num_waypoints"),
            "planner_version": planner_result.get("meta", {}).get("planner_version", "v1"),
            "validation_warnings": planner_result.get("meta", {}).get("validation_warnings"),
            "collision_flag": planner_result.get("meta", {}).get("collision_flag", False),
        },
        status="completed",
    )

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {str(exc)}")

    return _db_to_trajectory_response(db_obj)


@router.get(
    "/",
    response_model=List[TrajectoryResponse],
    summary="List trajectories (paginated)",
)
def list_trajectories(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[TrajectoryResponse]:
    """
    Return a (small) page of trajectory records. For demo use only.
    """
    rows = db.query(TrajectoryDB).order_by(TrajectoryDB.created_at.desc()).limit(limit).offset(offset).all()
    return [_db_to_trajectory_response(r) for r in rows]


@router.get(
    "/{trajectory_id}",
    response_model=TrajectoryResponse,
    summary="Fetch a single trajectory by id",
)
def get_trajectory(
    trajectory_id: int,
    db: Session = Depends(get_db),
) -> TrajectoryResponse:
    """
    Fetch the trajectory record with the given id.
    """
    row = db.query(TrajectoryDB).filter(TrajectoryDB.id == trajectory_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Trajectory not found")
    return _db_to_trajectory_response(row)






