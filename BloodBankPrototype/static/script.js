const groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const hospitals = ["City Hospital", "North Hospital", "East Hospital", "South Hospital"];
const $ = id => document.getElementById(id);

function fillSelect(id, items) {
  $(id).innerHTML = items.map(x => `<option value="${x}">${x}</option>`).join("");
}
fillSelect("invGroup", groups);
fillSelect("reqGroup", groups);
fillSelect("hospital", hospitals);
fillSelect("routeHospital", hospitals);

let toastTimer;
function toast(message, isError=false) {
  const el = $("toast");
  el.textContent = message;
  el.style.background = isError ? "#a52f3c" : "#173557";
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}
async function api(url, options={}) {
  const response = await fetch(url, {
    headers: {"Content-Type":"application/json"},
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
async function refresh() {
  const data = await api("/api/dashboard");
  $("totalUnits").textContent = data.total_units;
  $("pendingCount").textContent = data.pending_requests;
  $("lowStock").textContent = data.low_stock;
  $("inventory").innerHTML = data.inventory.map(item => `
    <div class="blood-card ${item.units <= item.min_stock ? "low" : ""}">
      <div class="blood-symbol">${esc(item.blood_group)}</div>
      <strong>${item.units}</strong><small>units available</small>
    </div>`).join("");
  $("requestsBody").innerHTML = data.requests.map(r => `
    <tr>
      <td>#${r.id}</td><td>${esc(r.hospital)}</td><td><b>${esc(r.blood_group)}</b></td>
      <td>${r.units}</td><td><span class="urgency ${r.urgency.toLowerCase()}">${esc(r.urgency)}</span></td>
      <td><span class="status ${r.status.toLowerCase()}">${esc(r.status)}</span></td>
      <td><button class="table-action" data-allocate="${r.id}" ${r.status !== "Pending" ? "disabled" : ""}>Allocate + route</button></td>
    </tr>`).join("");
  $("emptyRequests").style.display = data.requests.length ? "none" : "block";
  // Show requests in urgency order in the interface, then newest first within equal urgency.
  const urgencyRank = {Critical:0, High:1, Normal:2};
  const sorted = [...data.requests].sort((a,b) => {
    if (a.status !== b.status) return a.status === "Pending" ? -1 : 1;
    return urgencyRank[a.urgency] - urgencyRank[b.urgency] || b.id - a.id;
  });
  $("requestsBody").innerHTML = sorted.map(r => `
    <tr>
      <td>#${r.id}</td><td>${esc(r.hospital)}</td><td><b>${esc(r.blood_group)}</b></td>
      <td>${r.units}</td><td><span class="urgency ${r.urgency.toLowerCase()}">${esc(r.urgency)}</span></td>
      <td><span class="status ${r.status.toLowerCase()}">${esc(r.status)}</span></td>
      <td><button class="table-action" data-allocate="${r.id}" ${r.status !== "Pending" ? "disabled" : ""}>Allocate + route</button></td>
    </tr>`).join("");
}
$("inventoryForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const result = await api("/api/inventory", {method:"POST", body:JSON.stringify({
      blood_group:$("invGroup").value, units:$("invUnits").value
    })});
    toast(result.message); $("invUnits").value = ""; await refresh();
  } catch(err) { toast(err.message, true); }
});
$("requestForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const result = await api("/api/requests", {method:"POST", body:JSON.stringify({
      hospital:$("hospital").value, blood_group:$("reqGroup").value,
      units:$("reqUnits").value, urgency:$("urgency").value
    })});
    toast(result.message); await refresh();
  } catch(err) { toast(err.message, true); }
});
$("requestsBody").addEventListener("click", async e => {
  const button = e.target.closest("[data-allocate]");
  if (!button) return;
  button.disabled = true;
  try {
    const result = await api(`/api/allocate/${button.dataset.allocate}`, {method:"POST", body:"{}"});
    $("routeResult").innerHTML = `<span class="route-icon">✓</span><div><strong>Allocation successful</strong><p>${result.units} unit(s) of ${esc(result.blood_group)} allocated.<br>Route: ${result.path.map(esc).join(" → ")}<br>Estimated sample distance: <b>${result.distance} km</b></p></div>`;
    toast("Request allocated and shortest route calculated."); await refresh();
  } catch(err) { toast(err.message, true); button.disabled = false; }
});
$("routeButton").addEventListener("click", async () => {
  try {
    const result = await api("/api/route", {method:"POST", body:JSON.stringify({hospital:$("routeHospital").value})});
    $("routeResult").innerHTML = `<span class="route-icon">↗</span><div><strong>Shortest route found</strong><p>${result.path.map(esc).join(" → ")}<br>Sample distance: <b>${result.distance} km</b><br><small>${esc(result.algorithm)}</small></p></div>`;
  } catch(err) { toast(err.message, true); }
});
$("resetButton").addEventListener("click", async () => {
  if (!confirm("Reset stock and delete all demo requests?")) return;
  try { const result = await api("/api/reset", {method:"POST", body:"{}"}); toast(result.message); $("routeResult").innerHTML = '<span class="route-icon">↗</span><p>Choose a destination to calculate the shortest route from the Central Blood Bank.</p>'; await refresh(); }
  catch(err) { toast(err.message, true); }
});
refresh().catch(err => toast(err.message, true));
