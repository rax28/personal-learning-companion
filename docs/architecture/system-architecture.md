# System architecture
Frontend owns UI/offline device state. Express owns authentication, application APIs, persistence coordination and sync. FastAPI owns companion intelligence. Learner state is provider-independent.

`Frontend -> Express -> AI Backend -> Model Router` with learner model, knowledge graph, memory, root-gap and teaching modules coordinated by the companion orchestrator.
