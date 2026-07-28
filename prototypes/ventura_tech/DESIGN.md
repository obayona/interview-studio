---
name: Ventura Tech
colors:
  surface: '#faf9fe'
  surface-dim: '#dad9df'
  surface-bright: '#faf9fe'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3f8'
  surface-container: '#eeedf3'
  surface-container-high: '#e9e7ed'
  surface-container-highest: '#e3e2e7'
  on-surface: '#1a1b1f'
  on-surface-variant: '#414755'
  inverse-surface: '#2f3034'
  inverse-on-surface: '#f1f0f5'
  outline: '#717786'
  outline-variant: '#c1c6d7'
  surface-tint: '#005bc1'
  primary: '#0058bc'
  on-primary: '#ffffff'
  primary-container: '#0070eb'
  on-primary-container: '#fefcff'
  inverse-primary: '#adc6ff'
  secondary: '#4c4aca'
  on-secondary: '#ffffff'
  secondary-container: '#6664e4'
  on-secondary-container: '#fffbff'
  tertiary: '#9e3d00'
  on-tertiary: '#ffffff'
  tertiary-container: '#c64f00'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c2c1ff'
  on-secondary-fixed: '#0c006a'
  on-secondary-fixed-variant: '#3631b4'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb595'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7c2e00'
  background: '#faf9fe'
  on-background: '#1a1b1f'
  surface-variant: '#e3e2e7'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 34px
    fontWeight: '700'
    lineHeight: 41px
    letterSpacing: -0.022em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.019em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 25px
    letterSpacing: -0.017em
  body-lg:
    fontFamily: Inter
    fontSize: 17px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.015em
  body-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: -0.012em
  label-md:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.01em
  mono-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  sidebar-width: 260px
  gutter: 16px
  margin-page: 40px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
---

## Brand & Style

The design system is engineered to emulate the precision and reliability of a native macOS application. It targets high-stakes technical interview preparation, necessitating an environment that feels stable, professional, and "focused." 

The visual style is **Minimalist with Glassmorphic accents**. It prioritizes content clarity through generous white space and a rigorous layout hierarchy. Emotional resonance is achieved through "Vibrancy"—the subtle bleeding of background colors through translucent surfaces—which creates a sense of depth and integration with the host OS environment. The interface should feel like a high-performance tool rather than a standard web application.

## Colors

The palette is rooted in the Apple HIG (Human Interface Guidelines). 

- **Primary Action:** Apple System Blue (#007AFF) is used exclusively for primary calls-to-action, active states, and focus indicators.
- **Secondary/System:** System Purple (#5856D6) is reserved for specialized technical indicators or "Expert" level badges.
- **Surface Strategy:** 
    - **Base:** Pure white (#FFFFFF) for the primary content canvas.
    - **Vibrancy:** Sidebars and utility panels use a translucent light gray with a high-degree backdrop blur (20px-30px) to simulate macOS "materials."
    - **Grayscale:** A range of neutrals from #1D1D1F (Text) to #F5F5F7 (Secondary Backgrounds).

## Typography

This design system uses **Inter** for the core UI to mimic San Francisco's humanist qualities and legibility. **Geist** is introduced for labels and technical data to provide a developer-centric, monospaced-adjacent feel in code snippets and metadata.

- **Tracking:** Tight letter-spacing (negative values) is applied to larger headlines to maintain the "desktop" look.
- **Hierarchy:** Use font weight rather than size to differentiate information. Body text is typically 15px—the macOS standard—to ensure high information density without sacrificing readability.
- **Code:** Any technical output or interview question logic must use the `mono-sm` level.

## Layout & Spacing

The layout follows a **structured sidebar-main model**.

- **Sidebar:** Fixed at 260px. It utilizes backdrop-filter blur and contains the primary navigation.
- **Content Area:** A fluid canvas with a maximum readable width of 1200px for text-heavy interview descriptions.
- **Grid:** A 12-column grid is used for dashboard views, but individual "Simulator" views (Code Editor + Video Feed) use a flexible split-pane model.
- **Spacing Rhythm:** Based on an 8px scale. Padding inside components is typically 12px or 16px to maintain a compact, "utility-first" feel.

## Elevation & Depth

Depth is communicated through **translucency and hard-molded shadows** rather than soft, ambient glows.

- **Level 0 (Base):** Flat white or light gray.
- **Level 1 (Cards/Inputs):** Subtle 1px border (#000000 at 10% opacity) with no shadow.
- **Level 2 (Modals/Popovers):** A crisp 0.5px border and a distinct drop shadow (0px 10px 30px rgba(0,0,0,0.15)) to simulate a window floating above the desktop.
- **Vibrancy:** Apply `backdrop-filter: blur(20px) saturate(180%)` to all sidebar and navigation elements.

## Shapes

The shape language is defined by the **Apple "Squircle."** 

- **Standard Elements:** Buttons and input fields use a 6px to 8px radius.
- **Containers:** Cards and main content panels use a 12px radius (`rounded-lg`).
- **Outer Windows:** Main application wrappers or large modals use 18px-24px (`rounded-xl`) to mimic the physical corners of a MacBook display.

## Components

- **Buttons:**
    - **Primary:** Filled Blue (#007AFF) with white text. Subtle inner-glow top-border.
    - **Secondary:** Light gray gradient or white with a 1px border. 
- **Lists (Sidebar):** Hover states should use a light gray highlight with rounded corners (6px), keeping the text black. Active states use System Blue background with white text.
- **Input Fields:** Inset appearance with a subtle 1px border. On focus, a 2px blue "halo" (focus-ring) is applied.
- **Chips/Badges:** Small, pill-shaped with low-contrast background fills (e.g., light blue background with dark blue text) for status indicators like "Difficulty" or "Language."
- **Split-Pane:** A thin 1px vertical divider between the code editor and the interview prompt. The handle should be a subtle 2px vertical line visible only on hover.
- **Traffic Lights:** Window control icons (Red, Yellow, Green) should be present in the top-left of the main application shell to reinforce the macOS aesthetic.