# Final Companion Architecture

```text
                         PERSONAL LEARNING COMPANION

     SOURCE WORLD                                      LEARNER WORLD

 source URL / notes                                learner conversation
        │                                                  │
        ▼                                                  ▼
     ingest                                               state
        │                                                  │
        ▼                                                  ▼
     chunking                                           evidence
        │                                                  │
        ▼                                                  ▼
 model predictability                              prerequisite gap
        │                                                  │
        ▼                                                  ▼
 lossless source cache                              adaptive teaching
        │                                                  │
        ▼                                                  ▼
 relevant retrieval                                  assessment
        │                                                  │
        └───────────────► companion ◄──────────────────────┘
                              │
                              ▼
                           response
                              │
                              ▼
                      mastery + history
                              │
                              ▼
                        learner graph
```

## Separation of knowledge

The source cache answers: **what does the supplied material establish?**

The learner model answers: **what has this learner demonstrated, misunderstood, or left unresolved?**

The companion uses both without treating source exposure as proof of mastery.

## Conversation policy

The orchestrator is explicitly instructed to behave conversationally: respond to the latest message first, keep replies short by default, teach one idea at a time, use concrete examples when needed, avoid canned praise, ask at most one useful question, and resume saved topic state instead of restarting lessons.
