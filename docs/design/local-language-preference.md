# Frontend Localization Preference

## Problem Definition

The account menu needs a visible language switcher for EU languages. The project English-only rule applies to developer-facing documentation, engineering notes, code comments, and operational instructions. User-facing interface copy may be localized through reviewed frontend dictionaries.

## Options

| Option | Result | Tradeoff |
| --- | --- | --- |
| Add full translation catalogs now | UI copy changes per language. | Broad surface area; must keep translations clearly separated from developer-facing docs. |
| Use an external translation service | Fast visible translation. | Adds privacy, network, cost, quality, and compliance risks outside P0. |
| Add a local language preference selector with local dictionaries | Gives reviewers a testable switcher, stores intent locally, and localizes core UI copy. | Dynamic mock data may still render in source language until catalog coverage expands. |

Chosen option: local language preference selector in the account menu with static frontend dictionaries for core UI copy.

## State Machine

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| Default English preference | Open account menu | Account trigger exists | Menu open | Current preference is read from local browser storage. |
| Menu open | Select supported EU language | Language code is in the supported list | Preference selected | `lang`, `data-language-preference`, and local storage are updated; subscribed UI copy rerenders from the dictionary. |
| Preference selected | Reload app | Stored language code is supported | Preference restored | Selector shows the stored language and localized UI copy is restored. |
| Preference selected | Stored code is unknown | Unknown or missing value | Default English preference | Unknown value is ignored. |

## Impact Surface

- Account menu local controls.
- Browser localStorage preference state.
- Frontend i18n provider and static dictionaries.
- Frontend console contract and acceptance criteria.

No backend preference API, authentication, tenant setting, external translation service, mock payload, or production deployment behavior is added.

## Rollback Path

Remove the language selector, supported-language list, i18n provider, storage key, this design note, and the contract/acceptance bullets. Theme and utility-route account controls remain unaffected.

## Primitive Acceptance Criteria

- The account menu exposes a keyboard-accessible Language selector.
- The selector contains entries for the common EU official languages supported by the prototype preference list.
- Selecting a language stores the chosen code in local browser storage.
- Reloading the app restores the chosen code and core localized UI copy.
- Developer-facing documents and code comments remain English.
- The app uses local frontend dictionaries and does not call external translation services or backend preference storage in P0.
