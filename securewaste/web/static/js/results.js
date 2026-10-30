/**
 * Results page interactions.
 * Currently handles: copy masked value, toggle finding details (future), status updates (future).
 */

(() => {
  "use strict";

  // Initialize when DOM is ready
  document.addEventListener("DOMContentLoaded", () => {
    initCopyButtons();
    initSeverityMeterTooltips();
  });

  /**
   * Add copy-to-clipboard functionality for masked values.
   * Each masked value cell gets a copy button on hover/focus.
   */
  function initCopyButtons() {
    const valueCells = document.querySelectorAll(".sw-findings-cell--value");

    valueCells.forEach((cell) => {
      const codeEl = cell.querySelector(".sw-masked-value");
      if (!codeEl) return;

      const maskedValue = codeEl.textContent.trim();
      if (!maskedValue) return;

      // Create copy button
      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "sw-copy-btn";
      copyBtn.setAttribute("aria-label", "Copy masked value");
      copyBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      `;
      copyBtn.style.cssText = `
        margin-left: var(--sw-space-2);
        padding: 4px 8px;
        font-size: 0.7rem;
        background: transparent;
        border: 1px solid var(--sw-border);
        border-radius: var(--sw-radius-sm);
        color: var(--sw-text-muted);
        cursor: pointer;
        opacity: 0;
        transition: opacity 0.15s ease, color 0.15s ease, border-color 0.15s ease;
        display: inline-flex;
        align-items: center;
      `;

      // Show button on hover/focus of the cell
      cell.style.position = "relative";
      cell.appendChild(copyBtn);

      cell.addEventListener("mouseenter", () => {
        copyBtn.style.opacity = "1";
      });
      cell.addEventListener("mouseleave", () => {
        copyBtn.style.opacity = "0";
      });
      cell.addEventListener("focusin", () => {
        copyBtn.style.opacity = "1";
      });
      cell.addEventListener("focusout", () => {
        copyBtn.style.opacity = "0";
      });

      copyBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        try {
          await navigator.clipboard.writeText(maskedValue);
          showCopiedFeedback(copyBtn);
        } catch (err) {
          console.warn("Copy failed:", err);
          fallbackCopy(maskedValue, copyBtn);
        }
      });

      copyBtn.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          copyBtn.click();
        }
      });
    });
  }

  /**
   * Show visual feedback when copy succeeds.
   */
  function showCopiedFeedback(btn) {
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
    `;
    btn.style.color = "var(--sw-sev-low)";
    btn.style.borderColor = "var(--sw-sev-low)";

    setTimeout(() => {
      btn.innerHTML = originalHTML;
      btn.style.color = "";
      btn.style.borderColor = "";
    }, 1500);
  }

  /**
   * Fallback copy for browsers without clipboard API.
   */
  function fallbackCopy(text, btn) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
      showCopiedFeedback(btn);
    } catch (err) {
      console.error("Fallback copy failed:", err);
    } finally {
      document.body.removeChild(textarea);
    }
  }

  /**
   * Add tooltip-like behavior for severity meters.
   * Shows severity label on hover/focus.
   */
  function initSeverityMeterTooltips() {
    const meters = document.querySelectorAll(".sw-severity-meter");

    meters.forEach((meter) => {
      const label = meter.nextElementSibling;
      if (!label || !label.classList.contains("sw-severity-label")) return;

      // The label is already visible next to the meter, but we can enhance
      // accessibility by ensuring the meter itself has proper ARIA
      meter.setAttribute("role", "img");
      meter.setAttribute("aria-label", `Severity: ${label.textContent.trim()}`);
    });
  }
})();