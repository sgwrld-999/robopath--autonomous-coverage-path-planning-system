# RoboPath: Autonomous Coverage Path Planning System

A production-ready full-stack system for autonomous robot path planning, featuring complete coverage algorithms, real-time visualization, and a RESTful API.

## Project Overview

RoboPath is an end-to-end system designed for autonomous wall-finishing robots that need to cover surface areas efficiently while strictly avoiding obstacles. The project serves as a demonstration of complex algorithm implementation within a clean, production-grade software architecture.

**Key Technical Demonstrations:**

  * **Algorithm Design:** Custom boustrophedon (lawnmower) coverage algorithm with geometric interval subtraction.
  * **Backend Engineering:** Asynchronous FastAPI application utilizing dependency injection and proper routing.
  * **Database Design:** Relational mapping using SQLAlchemy with JSON field optimization for complex spatial data.
  * **Frontend Development:** Interactive trajectory visualizer using the HTML5 Canvas API.
  * **Testing:** Comprehensive suite of API and integration tests.

-----

## Key Features

### Core Capabilities

  * **Complete Coverage Planning:** Implements a boustrophedon algorithm to ensure 100% reachable surface coverage.
  * **Collision Avoidance:** automatically computes forbidden zones and inflates obstacles based on tool safety margins.
  * **Optimized Pathfinding:** Minimizes non-working transitions and redundant movements.
  * **Real-time Visualization:** interactive, canvas-based playback of the generated robot trajectory.
  * **Persistent Storage:** SQLite database (migratable to PostgreSQL) using SQLAlchemy ORM.
  * **RESTful API:** clean endpoint design with strict Pydantic data validation.

### Technical Highlights

  * Interval subtraction algorithm for efficient lane segmentation.
  * Rectangle merging logic for obstacle preprocessing.
  * Automatic orientation selection (vertical vs. horizontal sweep).
  * Configurable tool width, overlap, and safety margins.
  * Calculation of path length and coverage fraction metrics.

-----

## Technical Stack

### Backend

  * **Framework:** FastAPI (Async/Await)
  * **ORM:** SQLAlchemy (Declarative Models)
  * **Validation:** Pydantic v2
  * **Database:** SQLite (Development), PostgreSQL-ready
  * **Testing:** pytest, HTTPX

### Frontend(VIBE-CODED)

  * **Language:** Vanilla JavaScript (ES6+)
  * **Rendering:** HTML5 Canvas API (2D Context)
  * **Styling:** CSS3 (Flexbox/Grid)

### DevOps & Tooling

  * **Logging:** Middleware-based request timing and error logging
  * **CORS:** Configurable cross-origin resource sharing
  * **Static Files:** Integrated static file serving for the frontend

-----

## System Architecture

The system follows a layered architecture pattern, separating the presentation layer, API layer, domain logic, and data persistence.

```text
┌─────────────────────────────────────────────────────┐
│                   Client (Browser)                  │
│         Interactive Visualization Interface         │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP/JSON
┌─────────────────▼───────────────────────────────────┐
│             FastAPI Application                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Routers (API Endpoints)                     │   │
│  │  - POST /api/trajectories/                   │   │
│  │  - GET  /api/trajectories/                   │   │
│  │  - GET  /api/trajectories/{id}               │   │
│  └──────────────┬───────────────────────────────┘   │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐   │
│  │  Coverage Planner Service                    │   │
│  │  - Obstacle preprocessing                    │   │
│  │  - Lane generation                           │   │
│  │  - Interval subtraction                      │   │
│  │  - Waypoint discretization                   │   │
│  └──────────────┬───────────────────────────────┘   │
│                 │                                   │
│  ┌──────────────▼───────────────────────────────┐   │
│  │  Database Layer (SQLAlchemy)                 │   │
│  │  - Trajectory persistence                    │   │
│  │  - JSON field optimization                   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

-----

## Skills Demonstrated

### 1\. Algorithm Design & Implementation

Implemented custom computational geometry algorithms to solve the coverage path planning problem.

  * **Details:** Boustrophedon paths, rectangle merging, interval operations, collision detection.
  * **Key File:** `src/wall_done_planner.py`

### 2\. Backend Development

Architected a scalable REST API using modern Python standards.

  * **Details:** Dependency injection, middleware (logging/CORS), error handling, and database session management.
  * **Key Files:** `src/app.py`, `src/routers.py`

### 3\. Database Engineering

Designed a schema capable of handling both structured metadata and semi-structured spatial data.

  * **Details:** SQLAlchemy ORM modeling, JSON type usage for waypoints, schema migrations.
  * **Key File:** `src/database.py`

### 4\. API Design

Created a strict contract between frontend and backend.

  * **Details:** Pydantic schemas for request/response validation, OpenAPI/Swagger documentation, versioning.
  * **Key File:** `src/schema.py`

### 5\. Frontend Development

Built a lightweight, dependency-free visualization tool.

  * **Details:** Cartesian-to-canvas coordinate transformation, animation loops, async data fetching.
  * **Key Files:** `static/script.js`, `static/index.html`

### 6\. Testing

Ensured reliability through automated testing.

  * **Details:** Integration testing with FastAPI TestClient to validate endpoints and logic.
  * **Key File:** `test/test_api.py`

-----

## Installation & Setup

### Prerequisites

  * Python 3.9+
  * pip or poetry

### Quick Start

1.  **Clone the repository**

    ```bash
    git clone https://github.com/yourusername/robopath.git
    cd robopath
    ```

2.  **Create virtual environment**

    ```bash
    python -m venv venv
    # Linux/Mac:
    source venv/bin/activate
    # Windows:
    # venv\Scripts\activate
    ```

3.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application**

    ```bash
    uvicorn src.app:app --reload
    ```

5.  **Access the application**

      * Web Interface: `http://localhost:8000`
      * API Documentation: `http://localhost:8000/docs`

### Running Tests

```bash
pytest test/ -v
```

-----

## Usage Examples

### Web Interface

1.  Navigate to the local host URL.
2.  Input wall dimensions and tool parameters.
3.  Add obstacles via the "Add Obstacle" button.
4.  Click "Generate Trajectory" and use the playback controls to view the path.

### API Usage

**Create a Trajectory:**

```bash
curl -X POST "http://localhost:8000/api/trajectories/" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Kitchen Wall",
    "wall": {"width": 5.0, "height": 3.0},
    "obstacles": [
      {"x": 1.0, "y": 1.0, "width": 0.5, "height": 0.5}
    ],
    "planner_params": {
      "tool_width": 0.5,
      "overlap": 0.1,
      "safe_margin": 0.1,
      "orientation": "auto"
    }
  }'
```

**List Trajectories:**

```bash
curl "http://localhost:8000/api/trajectories/?limit=10"
```

**Get Single Trajectory:**

```bash
curl "http://localhost:8000/api/trajectories/1"
```

-----

## Algorithm Details

The planner implements a boustrophedon (lawnmower) pattern optimized for rectangular surfaces. The process follows these steps:

1.  **Obstacle Preprocessing:** Inflates obstacles by the safety margin, clips them to wall boundaries, and merges overlapping rectangles to simplify geometry.
2.  **Lane Generation:** Calculates lane spacing based on `tool_width * (1 - overlap)`.
3.  **Free Interval Computation:** Projects obstacles onto each lane and uses interval subtraction to identify free path segments.
4.  **Path Assembly:** Alternates lane direction, discretizes segments, and adds transition waypoints between lanes.
5.  **Validation:** Performs final collision checks against forbidden zones and calculates coverage metrics.

**Time Complexity:** O(N log N + L×N) where N is the number of obstacles and L is the number of lanes.

-----

## Database Schema

```sql
CREATE TABLE trajectories (
    id INTEGER PRIMARY KEY,
    job_name VARCHAR,
    created_at DATETIME,
    updated_at DATETIME,

    -- Wall configuration
    wall_width FLOAT NOT NULL,
    wall_height FLOAT NOT NULL,

    -- Inputs (JSON)
    obstacles JSON NOT NULL,
    planner_params JSON NOT NULL,

    -- Outputs (JSON)
    forbidden_rects JSON NOT NULL,
    waypoints JSON NOT NULL,
    meta JSON NOT NULL,

    -- Status tracking
    status VARCHAR DEFAULT 'completed',
    error_message VARCHAR
);
```

## Author

**Your Name**

  * GitHub: [@sgwrld](https://github.com/sgwrld-999)
  * LinkedIn: [worksiddhantgond]([https://linkedin.com/in/yourprofile](https://www.linkedin.com/in/worksiddhantgond/)
