# Version specification

A version is `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`.

## Parsing
- MAJOR, MINOR, PATCH are non-negative integers **without leading zeros** (`0` is fine, `01` is not).
- PRERELEASE is one or more dot-separated identifiers of `[0-9A-Za-z-]`. Identifiers must not be empty.
  A purely numeric identifier must not have leading zeros (`1.0.0-01` is invalid; `1.0.0-0a` is valid).
- BUILD metadata is dot-separated `[0-9A-Za-z-]` identifiers.
- Invalid input raises `ValueError`.

## Precedence
1. Compare MAJOR, MINOR, PATCH numerically, in that order.
2. A version with a prerelease has lower precedence than the same MAJOR.MINOR.PATCH without one.
3. Two prereleases are compared identifier by identifier, left to right:
   - numeric identifiers compare numerically;
   - alphanumeric identifiers compare lexically in ASCII order;
   - a numeric identifier always has lower precedence than an alphanumeric one;
   - if all shared identifiers are equal, the version with fewer identifiers has lower precedence.
4. BUILD metadata is ignored for precedence **and equality**: `1.0.0+a == 1.0.0+b`, and they hash equally.

Example order: `1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0`.

## Ranges
- `^X.Y.Z` means `>=X.Y.Z` and `<(X+1).0.0`.
  If X is 0, it means `>=0.Y.Z` and `<0.(Y+1).0`.
  If X and Y are both 0, it means `>=0.0.Z` and `<0.0.(Z+1)`.
- `~X.Y.Z` means `>=X.Y.Z` and `<X.(Y+1).0`.
- A version that has a prerelease never satisfies a range.
