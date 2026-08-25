# Review gate before PM-002

PM-002 must not begin until the corrections in `REVIEW_NOTES_PM001.md` are implemented and tested.

Reason: the next phase will build CRUD, configurable week/day/period setup, and bulk teaching assignments on top of these core relationships. Fixing teacher and project scope after PM-002 would create avoidable migrations and UI/API rework.
