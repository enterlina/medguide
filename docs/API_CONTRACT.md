# API Contract (Proposed)

**Status:** Draft. Elena and Kunal should confirm this schema before implementation.

## POST /api/analyze
Request:
```json
{
  "medications": [
    {"name": "Example Drug A", "dose": "10 mg"},
    {"name": "Example Drug B", "dose": "20 mg"}
  ]
}
```

Response (illustrative names and explanations only, **not medical findings**):
```json
{
  "analysis_id": "demo-001",
  "status": "completed",
  "medications": [
    {"input_name": "Example Drug A", "normalized_name": null, "match_status": "unverified"},
    {"input_name": "Example Drug B", "normalized_name": null, "match_status": "unverified"}
  ],
  "interactions": [
    {
      "medication_indices": [0, 1],
      "status": "insufficient_evidence",
      "severity": "unknown",
      "explanation": "Illustrative placeholder. No medication analysis has been performed.",
      "sources": []
    }
  ],
  "limitations": [
    "This response is synthetic mock data, not medical guidance."
  ]
}
```

## Design principles
- Use stable machine-readable values: `documented`, `insufficient_evidence`, `ambiguous`, `not_evaluated`.
- Include readable source title, URL, retrieval date and document identifier when available.
- Do not imply absence of identified interactions means the regimen is safe.
- Allow frontend to render pending, failed, ambiguous and insufficient-evidence states.
- Separate patient-provided data, retrieved facts and model explanations.
- Provide `GET /health` for system status; this is not a medical safety check.

## Integration process
1. Elena builds screens against agreed synthetic mock JSON.
2. Kunal builds the actual endpoint with the same schema.
3. Both validate field types, empty states, error handling and source references.
4. Document any breaking API change in a pull request.
