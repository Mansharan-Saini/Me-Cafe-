// This script loads Oracle data and submits forms to Flask.
(() => {
  const $ = (selector) => document.querySelector(selector);
  const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
  const currencyFormat = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

  function showMessage(text, isError = false) {
    const message = $("#message");
    message.textContent = text;
    message.classList.toggle("error", isError);
  }

  async function api(path, options = {}) {
    const response = await fetch(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers }
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Request failed.");
    return result;
  }

  function escapeText(value) {
    const span = document.createElement("span");
    span.textContent = value ?? "";
    return span.innerHTML;
  }

  function statusLabel(status) {
    const label = status === "SAFE" ? "SAFE" : status;
    const icon = { EXPIRED: "×", TODAY: "●", URGENT: "!", SOON: "◷", SAFE: "✓" }[status] || "•";
    return `<span class="status ${String(status).toLowerCase()}">${icon} ${escapeText(label)}</span>`;
  }

  async function loadAll() {
    try {
      const [summary, inventory, alerts, waste] = await Promise.all([
        api("/dashboard"), api(`/inventory?search=${encodeURIComponent($("#search").value)}`),
        api("/alerts"), api("/waste")
      ]);
      $("#summary").innerHTML = [
        ["Products", summary.product_count],
        ["Stock units", summary.stock_count],
        ["Expiring in 7 days", summary.expiring_count],
        ["Actual waste entries", summary.waste_count]
      ].map(([label, value]) => `<article><span>${label}</span><strong>${numberFormat.format(value || 0)}</strong></article>`).join("");

      $("#inventory").innerHTML = inventory.length ? inventory.map((item) =>
        `<tr><td>${escapeText(item.item_name)}</td><td>${escapeText(item.category_name)}</td><td>${numberFormat.format(item.quantity)} ${escapeText(item.unit)}</td><td>${escapeText(item.expiry_date.slice(0, 10))}</td><td>${statusLabel(item.expiry_status)}</td></tr>`
      ).join("") : '<tr><td colspan="5">No food items found.</td></tr>';

      $("#alerts").innerHTML = alerts.length ? alerts.map((alert) =>
        `<tr><td>${escapeText(alert.item_name)}</td><td>${statusLabel(alert.alert_type)}</td><td>${escapeText(alert.alert_date.slice(0, 10))}</td><td>${escapeText(alert.status)}</td></tr>`
      ).join("") : '<tr><td colspan="4">No expiry alerts. Select “Check expiry dates” to scan stock.</td></tr>';

      $("#waste").innerHTML = waste.length ? waste.map((row) =>
        `<tr><td>${escapeText(row.waste_date.slice(0, 10))}</td><td>${escapeText(row.item_name)}</td><td>${escapeText(row.reason_name)}</td><td>${numberFormat.format(row.quantity_wasted)} ${escapeText(row.unit)}</td><td>${currencyFormat.format(row.estimated_loss)}</td></tr>`
      ).join("") : '<tr><td colspan="5">No waste has been recorded.</td></tr>';

      fillChoices("#add-form [name=category_id]", await api("/categories"), "category_id", "category_name");
      fillChoices("#waste-form [name=item_id]", inventory, "item_id", "item_name");
      fillChoices("#waste-form [name=reason_id]", await api("/reasons"), "reason_id", "reason_name");
      fillChoices("#waste-form [name=user_id]", await api("/users"), "user_id", "username");
    } catch (error) {
      showMessage(error.message, true);
    }
  }

  function fillChoices(selector, rows, valueKey, labelKey) {
    const select = $(selector);
    const previous = select.value;
    select.innerHTML = `<option value="">Choose one</option>` + rows.map((row) =>
      `<option value="${row[valueKey]}">${escapeText(row[labelKey])}</option>`
    ).join("");
    if (rows.some((row) => String(row[valueKey]) === previous)) select.value = previous;
  }

  function formValues(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  function start() {
    $("#refresh").addEventListener("click", loadAll);
    $("#search").addEventListener("input", () => {
      window.clearTimeout(start.searchTimer);
      start.searchTimer = window.setTimeout(loadAll, 250);
    });
    $("#check-alerts").addEventListener("click", async () => {
      try {
        await api("/alerts/check", { method: "POST" });
        showMessage("Expiry check completed.");
        await loadAll();
      } catch (error) {
        showMessage(error.message, true);
      }
    });
    $("#add-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!event.currentTarget.reportValidity()) return;
      try {
        await api("/inventory", { method: "POST", body: JSON.stringify(formValues(event.currentTarget)) });
        event.currentTarget.reset();
        showMessage("Food item added.");
        await loadAll();
      } catch (error) {
        showMessage(error.message, true);
      }
    });
    $("#waste-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!event.currentTarget.reportValidity()) return;
      try {
        await api("/waste", { method: "POST", body: JSON.stringify(formValues(event.currentTarget)) });
        event.currentTarget.reset();
        showMessage("Waste recorded and stock updated.");
        await loadAll();
      } catch (error) {
        showMessage(error.message, true);
      }
    });
    loadAll();
  }

  document.addEventListener("DOMContentLoaded", start);
})();
