import {inspectNsp} from "./nsp-verify.mjs";

const base = document.getElementById("base");
const update = document.getElementById("update");
const status = document.getElementById("status");
const check = document.getElementById("check");

function line(x) {
  return x.kind.toUpperCase() + ": " + x.description +
    "\n  " + x.entries + " archive entries, " + x.nca + " NCA entries" +
    "\n  " + (x.bytes / 1e9).toFixed(3) + " GB; examined " +
    (x.indexBytes / 1024).toFixed(1) + " KiB of header/index.";
}
check.addEventListener("click", async () => {
  if (!base.files.length || !update.files.length) {
    status.className = "result bad";
    status.textContent = "Select both base and update NSP files first.";
    return;
  }
  check.disabled = true;
  status.className = "result";
  status.textContent = "Reading file indexes locally…";
  try {
    const b = await inspectNsp(base.files[0], "base");
    const u = await inspectNsp(update.files[0], "update");
    status.className = "result good";
    status.textContent = "Both NSP archive indexes are structurally valid.\n\n" +
      line(b) + "\n\n" + line(u) +
      "\n\nNo files were uploaded. This is not a verified native Odyssey build.";
  } catch (error) {
    status.className = "result bad";
    status.textContent = "Check incomplete: " + String(error.message || error);
  } finally {
    check.disabled = false;
  }
});
document.getElementById("clear").addEventListener("click", () => {
  base.value = "";
  update.value = "";
  status.className = "result";
  status.textContent = "Cleared. No file data was retained or transmitted.";
});
