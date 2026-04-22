# Issabel Concept Redesign

## Goal

Align the new switchable `terra` theme much more closely with the supplied concept image, while keeping it as an Issabel-selectable theme through `index.php?menu=themes_system` and preserving the branding overlay mechanism for future white-label variants.

This is not a dependency on `telephony_dashboard`. The redesign must stay isolated inside the theme overlay and work on top of the existing Issabel shell and modules.

## Approved Direction

- High visual fidelity to the concept, not a loose reinterpretation.
- Visible product brand should read as `Issabel`, not `Issabel Terra`.
- Keep the brand overlay infrastructure so the visible brand can be swapped later without rebuilding the shell.
- Sidebar should move closer to the concept and reuse Issabel's existing compact and expanded navigation behavior.
- The work should include both the global shell and a stronger visual facelift for `sysdash`, so the dashboard does not look legacy inside a modern frame.

## Chosen Approach

Use a controlled shell refit plus a dashboard facade:

1. Rework the theme shell templates and base CSS so the layout, spacing, hierarchy, and interaction patterns match the concept much more closely.
2. Re-skin the `sysdash` content area and dashboard widgets so the first authenticated screen looks coherent with the new shell instead of remaining obviously legacy.

This approach is preferred over a CSS-only pass because the current theme structure is too far from the concept in navigation density, header composition, and card rhythm. It is preferred over a module rewrite because the user wants a selectable Issabel theme, not a separate frontend.

## Scope

### In Scope

- `themes/terra/_common/index.tpl`
- `themes/terra/_common/_menu.tpl`
- `themes/terra/_common/login.tpl`
- `themes/terra-base/terra.css`
- `themes/terra-base/terra.js`
- Theme branding primitives and fallback assets
- `sysdash` presentation through theme-level styling and targeted overrides

### Out of Scope

- Replacing Issabel module logic
- Depending on `telephony_dashboard`
- Rewriting chart generation internals
- Modifying core Issabel theme selection behavior
- Overwriting or deleting existing themes like `tenant`

## Visual System

### Brand Layer

The visible wordmark should be `Issabel`.

Brand rendering should still be abstracted into theme-level primitives so that future brand overlays can replace:

- icon mark
- wordmark
- auxiliary label
- avatar and loader fallback assets

without requiring structural template changes.

### Sidebar

The sidebar should move from card-heavy grouped navigation to a flatter, lighter, concept-driven rail:

- pale surface with minimal borders
- small Issabel lockup at the top
- compact search field
- icon-plus-label rows with generous vertical rhythm
- subtle active state rather than heavy boxed groups
- clean compact mode using the existing Issabel collapse behavior

Expanded mode should prioritize readability. Compact mode should preserve recognizability through icons and spacing, not through decorative containers.

### Topbar

The topbar should follow the concept's lighter layout:

- more whitespace
- centered or visually centered search
- lightweight utility actions on the right
- cleaner user chip
- reduced visual noise around breadcrumbs and page title

The current heavy shell identity and explanatory copy should be removed from the main dashboard header. The content title should be allowed to lead.

### Content Surface

The content area should feel brighter, flatter, and more restrained:

- off-white background
- large cards with soft shadow
- nearly invisible borders
- more spacing between sections
- typography closer to the concept's clean dashboard rhythm

The current warmer editorial tone should be dialed back so the UI reads as a modern operations console, not as a branded showcase.

## Sysdash Treatment

The system dashboard must be visually adapted to the new shell so it resembles the concept's first screen.

### Widget Containers

Dashboard widgets should be normalized into consistent cards:

- unified radius
- consistent padding
- quiet header bars
- right-aligned refresh affordances
- cleaner title hierarchy

### Service Status Panel

Rows should be restyled toward the concept:

- cleaner icon alignment
- thinner separators
- status pills with clearer green / blue / red signaling
- reduced bevel and legacy chrome

### Charts And Metric Blocks

The underlying data and rendering can remain legacy, but the framing should be modernized:

- better spacing around charts
- cleaner legends
- softer grid lines
- clearer headline values
- stronger grouping between related metrics

The target is perceptual fidelity, not pixel-perfect cloning of the reference chart engine.

## Interaction

- Keep theme selection compatible with `themes_system`.
- Preserve compact/expanded sidebar behavior.
- Preserve current module routing and authentication flow.
- Keep all vendor assets local.

## Risks And Mitigations

### Legacy Widget Markup Variability

Risk: `sysdash` widgets may have inconsistent HTML that resists a perfectly uniform redesign.

Mitigation: style by stable containers first, then patch obvious outliers with targeted selectors inside the theme rather than changing module logic.

### Compact Navigation Regressions

Risk: making the sidebar too concept-faithful could hurt discoverability in Issabel's deeper menu tree.

Mitigation: preserve the existing collapse behavior and keep labels readable in expanded mode; compact mode is visual compression, not structural feature removal.

### Brand Overlay Drift

Risk: hard-coding visible `Issabel` everywhere would make future white-label work expensive.

Mitigation: centralize visible brand primitives and fallback assets in the theme overlay, even if the initial visible brand is `Issabel`.

## Verification

The implementation will be considered complete when:

1. Login screen clearly follows the concept direction more closely than the current warm editorial variant.
2. Authenticated shell shows a concept-aligned sidebar and topbar.
3. `sysdash` visually fits the new shell and no longer feels like an untouched legacy page.
4. Theme remains switchable through `themes_system`.
5. No dependency on `telephony_dashboard` is introduced.
6. Existing overlay structure and local asset loading continue to work.

## Implementation Intent

After spec approval, implementation planning should focus on:

1. shell layout convergence
2. brand primitive refactor
3. dashboard widget restyling
4. verification in the running Issabel container
