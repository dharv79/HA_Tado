# Releasing

Version lives in `custom_components/tado_resume/manifest.json`. A release is created by pushing a `release/<version>` branch; `.github/workflows/release.yml` then creates the tag and release at that commit and deletes the trigger branch. This works from Claude Code cloud sessions, which can push branches but not tags and have no `gh` CLI.

## Rules
- Tag = version exactly. `X.Y.Z` is a normal (latest) release; `X.Y.ZbN` is a prerelease.
- Notes: `RELEASE_NOTES.md` at the repo root on the release commit is used if present; otherwise GitHub auto-generates notes from merged PRs.
- Only release from the merged head of `main`, never from a feature branch or unmerged commit.
- The trigger branch version must match `manifest.json` on that commit.
- Never reuse a version. If a release is wrong, bump the version and release again; do not delete and recreate the tag.
- Release automatically once a piece of work is merged (standing user instruction). Automated notifications are not approval for anything else.

## Procedure
1. **Bump PR:** on the dev branch set the new version in `manifest.json`. For hand-written notes also add `RELEASE_NOTES.md` (what is new, fixes, any user action required). Open a PR to `main`, wait for the Tests check to pass, squash-merge.
2. **Trigger:**
   `git fetch origin main && git push origin origin/main:refs/heads/release/<version>`
   Retry only on network errors, up to 4 times, backing off 2s, 4s, 8s, 16s.
3. **Verify** (GitHub MCP `actions_list`, `get_release_by_tag`): the "Create Release" run succeeded; release `<version>` exists, targets the merge commit, has the correct prerelease flag and expected notes; `release/<version>` has been deleted.
4. **Cleanup PR** (only if `RELEASE_NOTES.md` was added): remove it in a small follow-up PR so the next release does not reuse stale notes.

## Maintenance
Dependabot (`.github/dependabot.yml`) updates the pinned GitHub Actions monthly.
