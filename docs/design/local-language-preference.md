# Local Language Preference

## Problem Definition

The account menu needs a visible language switcher for EU languages. The current P0 project boundary remains English-only for repository content and UI copy, so the first safe slice records a local language preference without adding translated strings or external localization services.

## Options

| Option | Result | Tradeoff |
| --- | --- | --- |
| Add full translation catalogs now | UI copy changes per language. | Violates the current English-only repository boundary and adds a large content-review surface. |
| Use an external translation service | Fast visible translation. | Adds privacy, network, cost, quality, and compliance risks outside P0. |
| Add a local language preference selector | Gives reviewers a testable switcher and stores intent locally. | Interface copy remains English until the English-only boundary is changed. |

Chosen option: local language preference selector in the account menu.

## State Machine

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| Default English preference | Open account menu | Account trigger exists | Menu open | Current preference is read from local browser storage. |
| Menu open | Select supported EU language | Language code is in the supported list | Preference selected | `data-language-preference` and local storage are updated. |
| Preference selected | Reload app | Stored language code is supported | Preference restored | Selector shows the stored language. |
| Preference selected | Stored code is unknown | Unknown or missing value | Default English preference | Unknown value is ignored. |

## Impact Surface

- Account menu local controls.
- Browser localStorage preference state.
- Frontend console contract and acceptance criteria.

No translated UI copy, backend preference API, authentication, tenant setting, external translation service, mock payload, or production deployment behavior is added.

## Rollback Path

Remove the language selector, supported-language list, storage key, this design note, and the contract/acceptance bullets. Theme and utility-route account controls remain unaffected.

## Primitive Acceptance Criteria

- The account menu exposes a keyboard-accessible Language selector.
- The selector contains English-labeled entries for the common EU official languages supported by the prototype preference list.
- Selecting a language stores the chosen code in local browser storage.
- Reloading the app restores the chosen code.
- The app keeps interface copy in English and does not add translated strings, external translation calls, or backend preference storage in P0.
