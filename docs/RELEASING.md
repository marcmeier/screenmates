# Releasing

screenmates uses [Semantic Versioning](https://semver.org/). The version is written in one place,
`backend/app/version.py`; the API and the about page report it from there.

1. Move the entries under "Unreleased" in `CHANGELOG.md` into a new section `## X.Y.Z – YYYY-MM-DD`.
   Breaking changes and upgrade steps go under "Upgrading".
2. Set the same version in `backend/app/version.py`. A test fails if the two don't match.
3. Open a pull request, let CI pass, merge.
4. Tag the merge commit `vX.Y.Z` and push the tag. The release workflow (`.github/workflows/release.yml`)
   checks that the tag matches `version.py`, builds the Docker image for amd64 and arm64, pushes it to
   `ghcr.io/<owner>/screenmates` as `X.Y.Z`, `X.Y` and `latest`, and creates the GitHub release with that
   changelog section.

The first time, the container package is private: on GitHub, open the package's settings and make it
public, so `docker compose up` can pull it without logging in.

Dependencies: Dependabot opens monthly pull requests. To re-pin by hand after editing
`backend/requirements*.in`, run `make lock`.
