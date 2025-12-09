# Workflow Engine

A minimal workflow/graph engine similar to LangGraph, built with FastAPI and Python. This system allows you to define workflows as directed graphs with nodes, edges, state management, conditional branching, and loops.

## Features

- Node-based workflows: Define workflows as Python functions operating on shared state.
- Graph structure: Connect nodes with edges to control execution flow.
- Conditional branching: Route execution based on state conditions.
- Looping: Repeat nodes until conditions are met.
- Tool registry: Reusable function library for workflow nodes.
- REST API: Create and run workflows via HTTP endpoints.
- WebSocket support: Stream real-time execution logs.
- Async execution: Background task support for long-running workflows.
- Sample workflow: Data Quality Pipeline demonstrating all features.

## Project Structure

workflow-engine/
├── app/
│ ├── init.py
│ ├── main.py # FastAPI app entry point
│ ├── api/
│ │ ├── init.py
│ │ └── routes_graph.py # Graph API endpoints
│ ├── engine/
│ │ ├── init.py
│ │ ├── models.py # Pydantic models
│ │ ├── engine.py # Core execution engine
│ │ ├── registry.py # Tool registry
│ │ └── storage.py # In-memory storage
│ └── workflows/
│ ├── init.py
│ └── data_quality.py # Sample workflow
├── tests/
│ ├── init.py
│ ├── test_engine.py # Engine tests
│ ├── test_registry.py # Registry tests
│ └── test_workflow.py # Workflow tests
├── .gitignore
├── requirements.txt
└── README.md

text

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Setup

1. Clone or download the repository.

2. Create a virtual environment (recommended):

python -m venv venv

On Windows
venv\Scripts\activate

On Mac/Linux
source venv/bin/activate

text

3. Install dependencies:

pip install -r requirements.txt

text

## Running the Application

### Start the server

uvicorn app.main:app --reload

text

Or:

python -m app.main

text

The API will be available at: `http://localhost:8000`

### API docs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### 1. POST `/graph/create`

Create a new workflow graph.

**Request body (example):**

{
"nodes": {
"profile": {
"id": "profile",
"type": "tool",
"tool_name": "profile_data",
"params": {}
},
"identify": {
"id": "identify",
"type": "tool",
"tool_name": "identify_anomalies",
"params": {"null_threshold": 0.1}
},
"generate": {
"id": "generate",
"type": "tool",
"tool_name": "generate_rules",
"params": {}
},
"apply": {
"id": "apply",
"type": "tool",
"tool_name": "apply_rules",
"params": {}
},
"check": {
"id": "check",
"type": "router",
"params": {}
}
},
"edges": [
{"source": "profile", "target": "identify"},
{"source": "identify", "target": "generate"},
{"source": "generate", "target": "apply"},
{"source": "apply", "target": "check"},
{
"source": "check",
"target": "identify",
"condition": "state.get("anomaly_count", 0) > 5"
}
],
"start_node": "profile"
}

text

**Response:**

{
"graph_id": "your-graph-id"
}

text

### 2. POST `/graph/run`

Run a graph with an initial state.

**Request body (example):**

{
"graph_id": "your-graph-id",
"initial_state": {
"data": [
{"id": 1, "name": "Alice", "age": 25, "salary": 50000},
{"id": 2, "name": "Bob", "age": null, "salary": 60000},
{"id": 3, "name": "Charlie", "age": 35, "salary": 999999}
]
},
"async_execution": false
}

text

**Response (sync example):**

{
"run_id": "your-run-id",
"status": "completed",
"state": { "...": "..." },
"log": [ "...steps..." ]
}

text

### 3. GET `/graph/state/{run_id}`

Get the current state and log of a run.

**Response:**

{
"run_id": "your-run-id",
"graph_id": "your-graph-id",
"status": "completed",
"current_node_id": null,
"state": { "...": "..." },
"log": [ "...steps..." ]
}

text

### 4. WS `/graph/ws/logs/{run_id}`

WebSocket endpoint to stream execution logs in real time.

## Sample Workflow: Data Quality Pipeline

The included workflow (Option C) does:

1. `profile_data` – profile dataset.
2. `identify_anomalies` – find nulls, outliers, duplicates.
3. `generate_rules` – derive rules from anomalies.
4. `apply_rules` – clean data and update anomaly count.
5. `check` node – if `anomaly_count` > threshold, loop back; otherwise finish.

You can use the example payloads above to test it.

## Testing

Run all tests:

pytest tests/ -v

text

Run a specific test file:

pytest tests/test_engine.py -v

text

## What this engine supports

- Nodes: Python functions reading and modifying shared state.
- State: Simple dictionary passed through the graph.
- Edges: Control flow with optional conditions.
- Branching: Conditional routing using expressions on `state`.
- Looping: Edges that route back while a condition is true.
- Tool registry: Central place to register and reuse tools.

## Possible future improvements (for the assignment write-up)

- Persist graphs and runs in SQLite/Postgres instead of in-memory.
- Add authentication and per-user graphs.
- Parallel execution of independent branches.
- Visual graph editor and export/import.
- More robust condition language (no raw `eval`).
