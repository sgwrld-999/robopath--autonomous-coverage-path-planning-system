# 10x-backend-assignment


## **1. Problem Formulation**

### **1.1 Understanding the Assignment**

The assignment described a backend system for a robot that performs **wall finishing**.
The backend must:

* Accept **wall dimensions** and **obstacles**
* Compute a **complete coverage path** while avoiding obstacles
* Persist the output in a **database**
* Expose the result through a **clean API**
* Provide clear logging and maintainable structure

However, the assignment did **not** specify:

* How obstacles should be represented
* How to generate the coverage path
* How the planner should work internally
* How data should be stored
* Whether coordinates are absolute or relative
* How much safety margin the robot requires
* What the expected coverage algorithm is

Therefore, the first task was to transform this high-level description into a **precise technical problem**.

---

### **1.2 Breaking Down the Problem**

I decomposed the system into four major components:

1. **Planner (Core Algorithm)**
    The logic that computes collision-free, complete coverage of the wall.

2. **Backend Server (FastAPI)**
    Accepts requests, validates input, invokes planner, returns results.

3. **Database Layer (SQLAlchemy + SQLite)**
    Persists trajectories, obstacles, metadata, and planner parameters.

4. **API Models & Router**
    Defines request/response schemas and the public interface.

This decomposition ensured that each component has a clear responsibility.

---

### **1.3 Requirements & Constraints Identified**

From the problem description, I extracted key requirements:

#### **Functional**

* Input: wall size, obstacles, planner parameters
* Output: ordered waypoints for brushing
* Must avoid obstacles
* Must cover all reachable wall area
* Must save planner output to DB
* Must expose API to retrieve trajectories

#### **Technical**

* Use FastAPI
* Use a database (SQLite for local development)
* Clean logs
* Modularity and minimal code footprint
* Suitable for extension later

#### **Constraints**

* Obstacles may lie anywhere
* Planner must tolerate ambiguous inputs
* Tool width and overlap affect lane spacing
* Robot requires safety margin (inflation around obstacles)

#### **Assumptions Made**

Because the assignment intentionally leaves some details open, I made the following assumptions:

* The wall coordinate system starts at **(0, 0)** — bottom-left corner.
* Obstacles are axis-aligned rectangles.
* Tool width (S) is given and lanes are spaced by
  `lane_spacing = S * (1 - overlap)`
* Obstacles must be *inflated* by a safe margin to avoid collisions.
* Boustrophedon (lawnmower) coverage is the intended pattern.
* SQLite is sufficient for storing trajectories for this assignment.

These assumptions enabled me to convert ambiguous statements into clear tasks.

---

## **2. Solution Approach**

### **2.1 System Architecture**

The system follows a clean **three-layer architecture**:

```
[ API Layer (FastAPI) ]
          |
[ Planner Service ]
          |
[ Database Layer (SQLAlchemy + SQLite) ]
```

Each layer has a single, well-defined responsibility.

---

### **2.2 Technology Choices & Justifications**

#### **FastAPI**

* Lightweight and extremely fast
* Excellent Pydantic validation
* Auto-generated OpenAPI docs
* Seamless async middleware for logging
* Perfect for assignment-sized backend projects

#### **SQLite**

* Serves assignment/local development needs
* Requires no deployment overhead
* SQLAlchemy integrates cleanly
* JSON support allows dynamic structures

#### **SQLAlchemy**

* Provides ORM models
* Clean table creation and dependency injection
* Safer than raw SQL

#### **Pydantic v2**

* Clear data validation for request/response
* Enforces input constraints early
* Ensures clean output formatting

#### **Custom Planner**

* Required because no library supports wall coverage planning
* The boustrophedon algorithm is ideal for structured coverage
* Simple, deterministic, and easy to validate

---

### **2.3 System Design Decisions**

#### **Planner Structure**

I designed the planner with clearly separated concerns:

1. **Obstacle Preprocessing**

    * Inflate by safe margin
    * Clip to wall boundaries
    * Merge overlapping rectangles

2. **Lane Generation**

    * Vertical or horizontal
    * Based on tool width & overlap

3. **Interval Subtraction**

    * Project forbidden rectangles onto lanes
    * Subtract to obtain free segments

4. **Waypoint Generation**

    * Discretize each segment
    * Add transitions
    * Compute headings

This structure makes the planner testable and easy to reason about.

---

#### **Database Schema**

I chose a **single-table JSON-based schema** for this assignment to keep things simple:

* `trajectory`

  * wall dimensions
  * obstacles
  * planner parameters
  * forbidden rectangles
  * waypoints
  * metadata (coverage, path length, etc.)

Reasons:

* JSON fields remove the need for multiple joins
* Easy to convert from/to Pydantic models
* Perfect fit for demo-level application
* Respects assignment’s simplicity requirement

---

#### **API Design**

Endpoints:

* `POST /api/trajectories` → run planner + store trajectory
* `GET /api/trajectories` → list trajectories
* `GET /api/trajectories/{id}` → fetch trajectory

This API surface is clean, minimal, and covers all required functionality.

---

#### **Error Handling**

I included strong error handling:

* Planner configuration errors
* Collision detection
* DB errors
* Invalid inputs

This ensures robustness even under malformed input.

---

#### **Logging Middleware**

Each request logs:

* Path
* Method
* Status code
* Time taken

This provides observability and is helpful for debugging planner performance.

---

## **3. Implementation Breakdown**

### **3.1 Project Structure**

```
src/
  app.py
  routers.py
  database.py
  schema.py
  wall_done_planner.py
static/
test/
requirements.txt
README.md
```

Each file has a specific and isolated purpose.

---

### **3.2 Planner Implementation**

I implemented the planner in `wall_done_planner.py` following these steps:

#### **1. Obstacle Processing**

* Inflate each obstacle
* Clip to wall
* Merge overlapping blocks

#### **2. Lane Planning**

* Compute lane spacing
* Generate vertical or horizontal lanes

#### **3. Free Interval Computation**

* Project forbidden rectangles onto each lane
* Subtract intervals using standard DSA interval subtraction

#### **4. Segment Assembly**

* Order segments in boustrophedon sequence
* Alternate direction for efficient coverage

#### **5. Waypoint Construction**

* Discretize segments
* Insert transitions
* Compute orientations

#### **6. Collision Check**

* Verify no waypoint lies inside forbidden rects

#### **7. Metadata Generation**

* Path length
* Coverage estimate
* Warnings (if any)

---

### **3.3 Router Implementation**

The router exposes the planner via FastAPI:

1. Validate request
2. Run planner
3. Serialize output
4. Store in DB
5. Return Pydantic response object

I also added pagination in the list route and standardized error messages.

---

### **3.4 Database Implementation**

Using SQLAlchemy ORM:

* Created `TrajectoryDB` table
* JSON fields store planner outputs
* UTC timestamps for auditability
* Dependency-injected DB session
* Auto-table creation for SQLite

---

### **3.5 Testing & Verification**

I validated correctness by:

* Running planner on walls without obstacles
* Running planner on walls with central obstacles
* Verifying that:

  * lanes are split correctly
  * waypoints are ordered
  * no collisions occur
  * path length is reasonable
* Manually reviewing DB entries
* Checking JSON shape against Pydantic models

---

## **4. Final Outcome**

### **4.1 What the System Supports**

* Full planner execution
* Clean API for submission & retrieval
* JSON-based trajectory storage
* Logging & observability
* Modular architecture ready for extension

---

### **4.2 API Summary**

#### **POST /api/trajectories**

* Input: wall, obstacles, planner parameters
* Output: full trajectory

#### **GET /api/trajectories**

* Returns list of trajectories with pagination

#### **GET /api/trajectories/{id}**

* Returns one trajectory by ID

---

### **4.3 Performance & Scalability Considerations**

* SQLite is sufficient for assignment scale
* Planner is deterministic and runs in O(N log N + lanes*N)
* JSON fields reduce joins and speed up development
* Router and middleware are async-friendly

For production:

* Switch to PostgreSQL
* Add caching for repeated planner runs
* Use background tasks for large walls

---

### **4.4 Future Improvements**

* Add concurrency-friendly task runner (Celery/RQ)
* Add visualization endpoint
* Introduce obstacle validation tools
* Add path smoothing for smoother robot motion
* Expose more planner configurations
* Add versioning for planner algorithms

---

## **Conclusion**

This project demonstrates:

* Problem interpretation
* Structured breakdown of requirements
* Clean system architecture
* Robust planning algorithm
* Strong backend engineering discipline

The final system is modular, extensible, and easy to maintain, while remaining minimal and focused—aligned with the expectations of the assignment.
