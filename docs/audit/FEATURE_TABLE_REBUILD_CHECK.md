# Feature-table rebuild check (Step 5 acceptance test): stopped, differences reported

Date: 2026-10-29. The committed `backend/pipeline/feature_table.csv` was **not** overwritten, and no committed result was touched. The two rebuilt files are in a scratch folder outside the repository.

## What was done

1. Recorded the committed file's SHA-256: `161577ae...` (1,123 rows, 36 columns, LF line endings).
2. Added the configurable paths to `backend/pipeline/paths.py` and pointed `build_feature_table.py` at them (path-only change, working tree, **uncommitted**).
3. Rebuilt the table on this machine into a scratch file (`EV_FEATURE_TABLE`), using the raw sessions and decoded EEG that are present here. Runtime about 2.5 minutes.

## Result

| Rebuild | SHA-256 equal to committed? | What differs |
|---|---|---|
| A. The refactored script, unchanged logic | **No** | `eeg_missing` is true in all 1,123 rows (committed: 799 of 1,123), so every EEG feature column is empty |
| B. Same script with a version-independent timestamp conversion (diagnostic copy in scratch only) | **No** | line endings only, plus one cell (see below); `eeg_missing` 799 of 1,123, the same as committed |

### Cause of the large difference (A)

`load_eeg_pair` converts the decoded timestamps with `pd.to_datetime(...).astype("int64") / 1e3`. The comment in the script and D033 note that pandas parsed these as microsecond-precision, so the division by 1,000 yields milliseconds. This machine runs pandas 2.3.3, which parses them as nanosecond-precision, so the result is in microseconds, no decision window overlaps an EEG sample, and every row gets `eeg_missing = True`. The script therefore gives different output under different pandas versions; the committed table corresponds to the older behaviour. This is **not** caused by the path refactor.

### What remains different after fixing the unit (B)

- **Line endings.** The committed file uses LF; pandas on Windows writes CRLF. Content is otherwise identical.
- **One cell.** In one row, `gaze_dispersion` is `-0.0` in the committed file and `0.0` in the rebuild. Numerically equal; it is a signed-zero artefact that depends on the platform's floating-point behaviour. After normalising line endings the SHA-256 values still differ because of this one cell.
- All other 40,427 cells, the column order and the row order are identical.

So the committed table is reproducible from the raw data on this machine up to line endings and one signed zero, **provided the timestamp unit is handled explicitly**.

## Proposed fix (a documented deviation; not applied)

1. In `load_eeg_pair`, convert timestamps to milliseconds in a unit-independent way, for example `(pd.to_datetime(col, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) / pd.Timedelta(milliseconds=1)` (this is what the diagnostic copy used).
2. Write the CSV with `lineterminator="\n"` so the bytes do not depend on the operating system.
3. Normalise signed zeros before writing (add 0.0 to numeric columns), or accept the single cell as a known platform difference.
4. Then rebuild into a scratch file and compare checksums again; expected result: identical, or identical apart from the single signed-zero cell if step 3 is not applied.

If the fix is approved, the committed `feature_table.csv` should still not be replaced: the comparison is the acceptance test, and replacing a file that every registered run used would change the recorded checksums.

## State of the working tree

`backend/pipeline/paths.py` and `backend/pipeline/build_feature_table.py` contain the path-only edits and are **uncommitted**. The remaining scripts in `docs/audit/HARDCODED_PATHS.md` have not been touched. The 65 tests under `backend/pipeline` and `backend/fps` pass with those edits present.

## Critical review

- **What could be wrong:** the diagnostic rebuild B used a modified copy of the script that is not in the repository; the claim "all other cells identical" comes from comparing the two files as text; I did not run the older pandas version to confirm the microsecond behaviour, only the 2.3.3 behaviour and the script's own comment.
- **Not done:** the other twelve files' path edits, the `.gitignore` entry for the scratch folder, extending the guard test, any change to the committed table or registry.
