// Local-only NSP PFS0 index reader. Reads at most 16 MiB of header/index.
// Does not decrypt NCAs, request console keys, or transfer file contents.
const EXPECTED = Object.freeze({
  base: { title: "0100000000010000", version: "0" },
  update: { title: "0100000000010800", version: "393216" }
});
const MAX_INDEX = 16 * 1024 * 1024;
const MAX_FILES = 8192;
const ascii = new TextDecoder("utf-8", {fatal: true});
const fail = message => { throw new Error(message); };

export function identifyName(filename, kind) {
  if (!(kind in EXPECTED)) fail("Choose base or update.");
  const expected = EXPECTED[kind];
  const name = String(filename || "");
  const tid = /\[([\da-fA-F]{16})\]/.exec(name);
  const ver = /\[v(\d+)\]/i.exec(name);
  const title = tid ? tid[1].toUpperCase() : null;
  if (title && title !== expected.title) fail("Wrong " + kind + " title ID; expected " + expected.title + ".");
  if (ver && ver[1] !== expected.version) fail("Wrong " + kind + " NSP version; expected v" + expected.version + ".");
  return { title, version: ver ? ver[1] : null, labelsMatch: Boolean(title && ver), expected };
}
export async function inspectNsp(file, kind) {
  if (!file || typeof file.slice !== "function" || !Number.isSafeInteger(file.size)) fail("Select an NSP from Files.");
  if (!String(file.name).toLowerCase().endsWith(".nsp")) fail("This picker accepts .nsp files only.");
  const label = identifyName(file.name, kind);
  if (file.size < 16) fail("The NSP is too short.");
  const first = await file.slice(0,16).arrayBuffer();
  if (first.byteLength !== 16) fail("Could not read the NSP header.");
  const h = new DataView(first);
  if (h.getUint32(0, true) !== 0x30534650) fail("Not a standard PFS0 NSP archive.");
  const count = h.getUint32(4, true), stringsLen = h.getUint32(8, true);
  if (!count || count > MAX_FILES) fail("Unexpected NSP file count.");
  const indexEnd = 16 + count*24 + stringsLen;
  if (indexEnd > MAX_INDEX || indexEnd > file.size) fail("Invalid or unexpectedly large NSP index.");
  const index = await file.slice(16,indexEnd).arrayBuffer();
  if (index.byteLength !== indexEnd - 16) fail("Could not read the NSP file index.");
  const view = new DataView(index);
  const names = new Uint8Array(index, count*24, stringsLen);
  const paths = [];
  const limit = BigInt(file.size);
  for (let i=0; i<count; i++) {
    const o = i*24;
    const start = view.getBigUint64(o, true);
    const size = view.getBigUint64(o+8, true);
    const no = view.getUint32(o+16, true);
    if (no >= stringsLen) fail("An NSP filename points outside the index.");
    let end = no;
    while (end < stringsLen && names[end] !== 0) end++;
    if (end === stringsLen) fail("An NSP filename is not terminated.");
    let name;
    try { name=ascii.decode(names.slice(no,end)); }
    catch (_) { fail("Invalid UTF-8 in an NSP filename."); }
    if (!name || name.includes("/") || name.includes("\\")) fail("Unexpected path in NSP index.");
    if (BigInt(indexEnd)+start+size > limit) fail("An NSP content entry is outside the file.");
    paths.push(name);
  }
  const nca = paths.filter(n => /^[\da-f]{32}(?:\.cnmt)?\.nca$/i.test(n)).length;
  if (!nca) fail("No NCA files were found in the PFS0 table.");
  return {
    kind, name: file.name, bytes: file.size,
    archive: "PFS0", entries: count, nca,
    indexBytes: indexEnd, title: label.title, version: label.version,
    labelsMatch: label.labelsMatch,
    description: label.labelsMatch ? "Filename ID/version and PFS0 structure pass" : "PFS0 structure passes; filename does not independently confirm both ID and version",
    limitation: "This is a local structural check, not decryption, cryptographic integrity, or a runnable IPA."
  };
}
