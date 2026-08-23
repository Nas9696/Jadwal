# PM-002C UI Notes — Arabic Assignment Matrix

The assignment workspace should be fast for daily school use and should not visually imitate aSc Timetables.

## Primary mental model
The manager thinks in:
- الفصل الدراسي,
- المرحلة والصف والشعبة,
- المادة,
- المعلم,
- عدد الحصص الأسبوعية,
- الغرفة/المعمل.

Do not expose join-table/database terms in normal copy.

## Grid behavior
- rows are active sections in the selected term,
- columns are subjects,
- sticky subject header and section identity,
- each cell shows `المطلوب / المسند`, teacher chips, and a compact status,
- missing/partial/complete/over states must remain understandable without relying on color alone,
- filters for stage, grade, shift, section, subject and assignment status,
- large-school horizontal scrolling must preserve row/column context.

## Editing
A cell opens a right-side drawer or equivalent focused editor rather than navigating away.

The editor should show:
- section + subject context,
- curriculum demand,
- assignment groups already contributing to the cell,
- teacher selector with assigned load information,
- weekly count,
- resources,
- advanced option for combined sections/co-teaching,
- server warnings before save when load or curriculum is exceeded.

## Bulk workflow
Use explicit selection and a visible action bar. The safest first bulk operation is same-subject selection across multiple sections. Preview how many cells/assignments will change before destructive or replacement actions.

Do not implement an automatic assignment engine in PM-002C.