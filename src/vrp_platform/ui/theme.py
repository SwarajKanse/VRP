"""Shared visual design system for the NiceGUI application."""

from __future__ import annotations

from nicegui import ui


def apply_theme() -> None:
    """Inject the application theme and reusable visual tokens."""

    ui.add_head_html(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
          :root {
            --vrp-ink: #0d1b2a;
            --vrp-muted: #5f7390;
            --vrp-surface: rgba(255, 255, 255, 0.8);
            --vrp-surface-strong: rgba(255, 255, 255, 0.92);
            --vrp-line: rgba(13, 27, 42, 0.1);
            --vrp-accent: #ff7a00;
            --vrp-accent-deep: #d45a00;
            --vrp-ocean: #0f4c81;
            --vrp-success: #167c56;
            --vrp-warn: #b56c00;
            --vrp-danger: #b33a3a;
            --vrp-bg-a: #fff6e7;
            --vrp-bg-b: #e6f0ff;
            --vrp-bg-c: #f4f8fc;
          }
          body, .nicegui-content {
            font-family: "Plus Jakarta Sans", "Segoe UI", sans-serif;
            color: var(--vrp-ink);
            background:
              radial-gradient(circle at top left, rgba(255, 122, 0, 0.16), transparent 24rem),
              radial-gradient(circle at top right, rgba(15, 76, 129, 0.16), transparent 30rem),
              linear-gradient(180deg, var(--vrp-bg-a), var(--vrp-bg-b) 58%, var(--vrp-bg-c));
          }
          body::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
              linear-gradient(rgba(13, 27, 42, 0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(13, 27, 42, 0.03) 1px, transparent 1px);
            background-size: 36px 36px;
            mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.28), transparent 70%);
            opacity: 0.42;
          }
          .vrp-shell {
            max-width: 1480px;
            margin: 0 auto;
            padding: 1.4rem;
          }
          .vrp-panel {
            background: var(--vrp-surface);
            border: 1px solid var(--vrp-line);
            border-radius: 24px;
            box-shadow: 0 18px 52px rgba(13, 27, 42, 0.08);
            backdrop-filter: blur(14px);
          }
          .vrp-hero {
            background:
              linear-gradient(135deg, rgba(255, 122, 0, 0.94), rgba(13, 27, 42, 0.94)),
              linear-gradient(45deg, rgba(255, 255, 255, 0.08), transparent 70%);
            color: white;
            overflow: hidden;
          }
          .vrp-kpi-value, .vrp-mono {
            font-family: "IBM Plex Mono", monospace;
          }
          .vrp-subtle {
            color: var(--vrp-muted);
          }
          .vrp-pill {
            border-radius: 999px;
            padding: 0.22rem 0.7rem;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            background: rgba(13, 27, 42, 0.08);
          }
          .vrp-workspace {
            min-height: calc(100vh - 2rem);
            align-items: stretch;
          }
          .vrp-rail {
            width: 18rem;
            position: sticky;
            top: 1rem;
            gap: 1rem;
          }
          .vrp-rail-card {
            background:
              linear-gradient(180deg, rgba(13, 27, 42, 0.95), rgba(22, 41, 63, 0.94)),
              linear-gradient(45deg, rgba(255, 255, 255, 0.04), transparent);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 28px;
            color: white;
            box-shadow: 0 18px 44px rgba(13, 27, 42, 0.22);
          }
          .vrp-stage {
            min-width: 0;
          }
          .vrp-command {
            background:
              linear-gradient(135deg, rgba(13, 27, 42, 0.96), rgba(33, 69, 111, 0.92)),
              linear-gradient(45deg, rgba(255, 255, 255, 0.05), transparent);
            color: white;
            overflow: hidden;
            position: relative;
          }
          .vrp-command::after {
            content: "";
            position: absolute;
            inset: auto -18% -44% auto;
            width: 24rem;
            height: 24rem;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(255, 122, 0, 0.22), transparent 70%);
            pointer-events: none;
          }
          .vrp-overline {
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.72rem;
            font-weight: 700;
            opacity: 0.72;
          }
          .vrp-nav-button {
            width: 100%;
            justify-content: flex-start;
            border-radius: 16px;
            padding: 0.8rem 0.9rem;
          }
          .vrp-nav-active {
            background: rgba(255, 122, 0, 0.16);
            border: 1px solid rgba(255, 122, 0, 0.3);
          }
          .vrp-side-note {
            border-left: 3px solid rgba(255, 122, 0, 0.42);
            padding-left: 0.8rem;
          }
          .vrp-stat-card {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.74), rgba(255, 255, 255, 0.6));
            border: 1px solid rgba(13, 27, 42, 0.08);
            border-radius: 18px;
          }
          .vrp-tone-ready { color: var(--vrp-success); }
          .vrp-tone-warn { color: var(--vrp-warn); }
          .vrp-tone-danger { color: var(--vrp-danger); }
          .vrp-insight-card {
            background:
              linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(248, 251, 255, 0.72));
            border: 1px solid rgba(13, 27, 42, 0.08);
            border-radius: 22px;
            box-shadow: 0 14px 34px rgba(13, 27, 42, 0.07);
          }
          .vrp-insight-top {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
          }
          .vrp-meter {
            width: 100%;
            height: 10px;
            border-radius: 999px;
            background: rgba(13, 27, 42, 0.08);
            overflow: hidden;
          }
          .vrp-meter-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #0f4c81, #ff7a00);
          }
          .vrp-risk-stable {
            color: var(--vrp-success);
            background: rgba(22, 124, 86, 0.1);
          }
          .vrp-risk-watch {
            color: var(--vrp-warn);
            background: rgba(181, 108, 0, 0.12);
          }
          .vrp-risk-critical {
            color: var(--vrp-danger);
            background: rgba(179, 58, 58, 0.12);
          }
          .vrp-data-chip {
            border-radius: 14px;
            padding: 0.4rem 0.7rem;
            border: 1px solid rgba(13, 27, 42, 0.08);
            background: rgba(255, 255, 255, 0.72);
            font-size: 0.8rem;
          }
          .vrp-panel-title {
            font-family: "Space Grotesk", sans-serif;
            font-weight: 700;
            letter-spacing: -0.03em;
          }
          .q-btn.q-btn--standard {
            border-radius: 14px;
            text-transform: none;
            font-weight: 600;
          }
          .q-field--outlined .q-field__control,
          .q-select .q-field__control,
          .q-input .q-field__control {
            border-radius: 14px;
          }
          @media (max-width: 1280px) {
            .vrp-rail {
              width: 100%;
              position: static;
            }
          }
        </style>
        """,
        shared=True,
    )
