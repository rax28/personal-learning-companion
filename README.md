# Personal Learning Companion
personal-learning-companion-two.vercel.app

An AI-powered personalized learning platform that adapts its teaching to a learner’s knowledge, learning progress, and knowledge gaps.

Personal Learning Companion combines source-grounded AI tutoring, lossless source compression, intelligent retrieval, and a dynamic learner model to provide a personalized and context-aware learning experience.

## Key Features

- **Source-Based Learning:** Ingest learning materials and ground AI-generated explanations in relevant source content.
- **Lossless Source Compression:** Store learning source chunks in compressed form and retrieve relevant content when needed.
- **AI-Powered Tutoring:** Use configured AI providers and an offline Ollama model for context-aware learning assistance.
- **Personalized Learner Model:** Track learner evidence, concept mastery, learning progress, and knowledge gaps.
- **Adaptive Teaching:** Use learner progress and identified gaps to guide subsequent learning interactions.
- **Knowledge Graph:** Represent relationships between learning concepts to support concept mastery and gap identification.
- **Vector-Based Retrieval:** Use PostgreSQL and pgvector to store text embeddings and retrieve relevant learning content through similarity search.
- **Redis Caching:** Cache learning source data, search results, and knowledge graph information with time-based expiration to improve retrieval performance.
- **Google Classroom Integration:** Support learning resource ingestion through Google Classroom integration.
- **Persistent Learner State:** Store learner information and learning progress in persistent storage.
- **Full-Stack Architecture:** Integrate the frontend, backend API, Python AI service, and supporting data services.
- **Cloud Deployment:** Deploy the frontend on Vercel and backend services on Railway.

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
Source Storage and Cache
(PostgreSQL + Redis)
      |
      v
Embedding-Based Retrieval
(PostgreSQL + pgvector)
      |
      v
AI Provider / Ollama
      |
      v
Source-Grounded AI Tutoring
      |
      v
Learner Evidence and Progress
      |
      v
Mastery and Knowledge Gaps
      |
      v
Knowledge Graph and Learner State
```

## Technology Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Node.js, Express, TypeScript
- **AI Service:** Python, FastAPI
- **Language Models:** Configured AI providers and Ollama for local inference
- **Persistent Storage:** PostgreSQL
- **Vector Search:** pgvector
- **Caching:** Redis
- **Source Processing:** Chunking, lossless compression, and retrieval
- **Learning Integration:** Google Classroom APIs and Google OAuth
- **Deployment:** Vercel and Railway
- **Containerization:** Docker and Docker Compose

## How It Works

1. Add or import learning materials through the application.
2. Process the materials into chunks and store source content for retrieval.
3. Generate and store text embeddings for supported vector-search workflows.
4. Retrieve relevant content using similarity search and cached source data.
5. Provide retrieved evidence to the configured language model as context.
6. Generate explanations grounded in the available learning materials.
7. Use learning interactions to update learner evidence, mastery, and knowledge gaps.
8. Represent the learner’s evolving understanding through the knowledge graph and persistent learner state.

## Getting Started

### Prerequisites

- Git
- Node.js and npm
- Python 3 compatible with the AI service dependencies
- PostgreSQL with pgvector enabled
- Redis
- Docker and Docker Compose, if using the containerized setup
- AI-provider credentials or a configured Ollama model
- Google OAuth credentials, if using Google Classroom integration

### Clone the Repository

```bash
git clone https://github.com/rax28/personal-learning-companion.git
cd personal-learning-companion
```

### Configure Environment Variables

Configure the environment variables required by the frontend, backend, and AI service.

These may include database connection details, Redis connection settings, AI-provider credentials, internal service authentication, and Google OAuth configuration.

Never commit API keys, database passwords, OAuth secrets, or other credentials to the repository.

### Start the Application

If the repository contains a configured `compose.yaml` or `docker-compose.yml`, start the services with:

```bash
docker compose up --build
```

Check the repository's environment configuration and setup instructions before starting. Required environment variables, database initialization, model availability, and service ports may need to be configured first.

## Deployment

- **Frontend:** Deployed on Vercel.
- **Backend:** Deployed on Railway.
- **AI Service:** Deployed as a backend service, configured to communicate with the main API.
- **Database and Cache:** PostgreSQL and Redis provide persistent storage and caching, respectively.

The deployed services require correctly configured service URLs, database connections, credentials, CORS settings, and AI-provider access.

**Note:** Local Ollama inference requires the Ollama model to be accessible from the environment running inference. A model installed only on a developer’s computer is not automatically available to a cloud deployment.

## Project Goals

- Deliver personalized, evidence-based AI tutoring.
- Reduce repeated source processing through compressed source storage and caching.
- Connect relevant source retrieval directly to AI-generated explanations.
- Track learning progress through evidence, mastery, and knowledge gaps.
- Represent concept relationships using a knowledge graph.
- Combine cloud AI services with local model inference where supported.

## Current Development Focus

- Verifying the complete source-to-tutor pipeline.
- Testing learner-model updates after learning sessions.
- Validating persistence of mastery, knowledge gaps, and concept relationships.
- Testing embedding-based retrieval and Redis cache behavior.
- Validating Google Classroom integration.
- Testing the deployed frontend and backend services.

## License

No license has been specified yet. Add a license before distributing the project for reuse.
