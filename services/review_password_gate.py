"""
services/review_password_gate.py — App-level password gate for the
ForecastTrader external-review deployment.

Per Chris's password-gated handoff
(docs/deployments/forecasttrader_password_gated_review_deployment.md):
the deployment is a *public* Streamlit app gated by an in-app password
stored in Streamlit Secrets as ``review_password``. This is the
workaround for Streamlit Community Cloud's one-private-app-per-workspace
limit — the production private app stays untouched.

The gate is enabled when the Streamlit secret ``REVIEW_BUILD`` is set
to ``"true"``. That keeps the same code safely mergeable back to
``main``: production deployments without the secret remain ungated.

The password comparison uses :func:`hmac.compare_digest` to avoid
leaking timing information.

The gate UI is intentionally branded — Oriel logo, gold-accent header
chip, sample-data tagline, and the "illustrative review build" footer
that matches the rest of the app's design language. This is the first
screen Jose Torres and Rob Prior see when they open the link, so it
should look like a deliberate landing page, not Streamlit defaults.
"""
from __future__ import annotations

import hmac

import streamlit as st


def _logo_data_uri() -> str:
    """Lazy-load the Oriel logo data URI (defined in ui.nav)."""
    try:
        from ui.nav import LOGO_DATA_URI
        return LOGO_DATA_URI
    except Exception:
        return ""


def check_review_password() -> bool:
    """Return True iff a valid review password is in session state.

    Renders the branded password prompt UI as a side effect when not yet
    authenticated. Caller is expected to call ``st.stop()`` when this
    returns False so no review-only content renders.
    """

    def _password_entered() -> None:
        entered = st.session_state.get("review_password_input", "")
        try:
            expected = st.secrets.get("review_password", "")
        except Exception:
            expected = ""
        if expected and hmac.compare_digest(str(entered), str(expected)):
            st.session_state["review_password_correct"] = True
            # Don't keep the typed password in session state.
            del st.session_state["review_password_input"]
        else:
            st.session_state["review_password_correct"] = False

    if st.session_state.get("review_password_correct", False):
        return True

    # ── Branded login UI ─────────────────────────────────────────────────────
    logo_uri = _logo_data_uri()
    attempted = "review_password_correct" in st.session_state  # i.e. tried at least once

    # Hide the default header/main padding for a cleaner landing page,
    # then center the card in a narrow middle column.
    st.markdown(
        """
        <style>
          /* Push the login card down a bit so it sits in the optical center. */
          [data-testid="stMain"] .block-container { padding-top: 4vh; }
          /* Style the password input to match the dark-gold theme. */
          [data-testid="stTextInput"] input {
            background: #0f1620 !important;
            border: 1px solid #2a3a52 !important;
            border-radius: 8px !important;
            color: #E6EDF3 !important;
            font-family: 'Inter', system-ui, sans-serif !important;
            font-size: 0.85rem !important;
            padding: 10px 14px !important;
            letter-spacing: 0.04em !important;
          }
          [data-testid="stTextInput"] input:focus {
            border-color: #D4A85A !important;
            box-shadow: 0 0 0 2px rgba(212,168,90,0.18) !important;
            outline: none !important;
          }
          [data-testid="stTextInput"] input::placeholder {
            color: #5a6a80 !important;
            letter-spacing: 0.06em !important;
          }
          /* Tighten the error message under the input. */
          [data-testid="stAlert"] {
            border-radius: 8px !important;
            margin-top: 6px !important;
            font-size: 0.74rem !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    pad_l, center, pad_r = st.columns([1, 2, 1])

    with center:
        # Branded card
        st.markdown(
            f"""
            <div class='note-box' style='text-align:center; padding:34px 30px 28px;'>
              <div style='margin-bottom:18px;'>
                <img src='{logo_uri}' style='height:38px; opacity:0.96;' alt='Oriel'/>
              </div>
              <div style='font-size:1.25rem; color:#E6EDF3; font-weight:500;
                          letter-spacing:0.06em; margin-bottom:8px;'>
                Oriel CPI Demo
              </div>
              <div style='display:inline-block; font-size:0.6rem; color:#D4A85A;
                          letter-spacing:0.18em; text-transform:uppercase;
                          background:rgba(212,168,90,0.08);
                          border:1px solid rgba(212,168,90,0.25);
                          border-radius:999px; padding:3px 12px; margin-bottom:18px;'>
                ForecastTrader Review Build
              </div>
              <div style='font-size:0.78rem; color:#8fa3b8; line-height:1.6;
                          max-width:420px; margin:0 auto;'>
                Oriel converts discrete CPI event contracts into continuous,
                institution-grade macro surfaces. This review build is
                password-protected and uses sample data only.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Small spacer between card and input
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # Password input — uses Streamlit's text_input under the hood for the
        # session-state binding, but styled via the CSS block above.
        st.text_input(
            "Review password",
            type="password",
            on_change=_password_entered,
            key="review_password_input",
            label_visibility="collapsed",
            placeholder="Enter review password",
        )

        if attempted:
            st.error("Password incorrect. Please try again.")

        # Footer disclaimer (matches the gold-accent footer used everywhere
        # else in the app).
        st.markdown(
            "<div style='font-size:0.66rem; color:#7a8aa0; text-align:center;"
            "margin-top:20px; line-height:1.55; letter-spacing:0.02em;'>"
            "Illustrative review build &middot; Not production trading infrastructure"
            "</div>",
            unsafe_allow_html=True,
        )

    return False


def review_build_gate_enabled() -> bool:
    """Return True iff the password gate should be active for this deploy.

    Reads the ``REVIEW_BUILD`` value from Streamlit Secrets (per Chris's
    handoff Step 3). Defaults to False so production deployments without
    the secret stay open.
    """
    try:
        value = st.secrets.get("REVIEW_BUILD", "false")
    except Exception:
        value = "false"
    return str(value).strip().lower() == "true"
