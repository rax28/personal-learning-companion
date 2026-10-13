# Personal Learning Companion

An AI-powered personalized learning platform that adapts its teaching to a learner’s knowledge, learning progress, and knowledge gaps.

Personal Learning Companion combines source-grounded AI tutoring, lossless compression, intelligent retrieval, and a dynamic learner model to provide a more personalized and context-aware learning experience.

## Key Features

- **Source-Based Learning:** Ingest learning materials and use relevant source content to ground AI-generated explanations.
- **Lossless Source Compression:** Store source chunks in a compressed cache and retrieve only the relevant content when needed.
- **AI-Powered Tutoring:** Use Llama 3.2 through Ollama to generate context-aware explanations grounded in retrieved evidence.
- **Personalized Learner Model:** Track learner evidence, concept mastery, and knowledge gaps.
- **Adaptive Teaching:** Use learner progress and identified gaps to guide subsequent learning interactions.
- **Knowledge Graph:** Represent concepts and their relationships to support structured learning.
- **Persistent Learner State:** Maintain learner information separately from the source knowledge cache.
- **Full-Stack Architecture:** Integrate the frontend, backend API, AI service, and supporting data services.

## System Architecture

```text
Learning Sources
      |
      v
Source Ingestion
      |
      v
Chunking and Lossless Compression
      |
      v
Compressed Source Cache
      |
      v
Relevant Chunk Retrieval
      |
      v
Llama 3.2 / Ollama
      |
      v
Grounded AI Tutoring
      |
      v
Learner Evidence
      |
      v
Mastery and Knowledge Gaps
      |
      v
Knowledge Graph and Learner State
```

## Technology Stack

- **Frontend:** Web-based user interface
- **Backend:** API gateway and application services
- **AI Service:** Python, FastAPI
- **Language Model:** Llama 3.2 via Ollama
- **Data and Infrastructure:** PostgreSQL, Redis, Docker
- **Source Processing:** Chunking, lossless compression, and retrieval

*Note: Verify the exact technologies and service responsibilities against the current project configuration before publishing.*

## How It Works

1. Add learning materials through the Source Lab.
2. Process the materials into chunks and store them in a compressed cache.
3. Retrieve and decompress relevant chunks for a learning query.
4. Provide the retrieved evidence to the language model as context.
5. Generate an answer grounded in the available learning materials.
6. Use learning interactions to update learner evidence, mastery, and knowledge gaps.
7. Represent the learner’s evolving understanding through the knowledge graph and persistent state.

## Getting Started

### Prerequisites

- Git
- Docker and Docker Compose
- Python 3, if running Python services locally
- Ollama with the required Llama model, if running the AI service locally

### Clone the Repository

```bash
git clone https://github.com/rax28/personal-learning-companion.git
cd personal-learning-companion
```

### Start the Application

If the repository contains a configured `compose.yaml` or `docker-compose.yml`, start the services with:

```bash
docker compose up --build
```

Check the repository's environment configuration and setup instructions before starting the application. Required environment variables, model availability, database initialization, and service ports may need to be configured first.

## Project Goals

- Deliver personalized, evidence-based AI tutoring.
- Reduce repeated source processing through a compressed source cache.
- Connect retrieval directly to AI-generated explanations.
- Track learning progress using evidence, mastery, and knowledge gaps.
- Build a learner model that evolves through learning interactions.

## Current Development Focus

- Verifying the complete source-to-tutor pipeline.
- Testing learner-model updates after real learning sessions.
- Validating persistence of mastery, knowledge gaps, and concept relationships.
- Testing the integrated Docker deployment and AI service.

## License

No license has been specified yet. Add a license before distributing the project for reuse.