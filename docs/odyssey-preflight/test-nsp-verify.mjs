import assert from "node:assert/strict";
import {inspectNsp, identifyName} from "./nsp-verify.mjs";

const gameNames = {
  base: "Super Mario Odyssey [0100000000010000][v0].nsp",
  update: "SUPER MARIO ODYSSEY [0100000000010800][v393216][Update v1.4.1].nsp"
};
// Small synthetic PFS0 header+index; fake large-sized backing requires no ROM
// bytes and demonstrates that only a tiny, bounded header is read.
function fixture(kind, options = {}) {
  const names = options.noNca ? ["readme.txt"] :
    [ "a".repeat(32) + ".nca", "b".repeat(32) + ".cnmt.nca" ];
  const strs = new TextEncoder().encode(names.join("\0")+"\0");
  const idx = 16 + names.length * 24 + strs.length;
  const bytes = new Uint8Array(idx);
  const view = new DataView(bytes.buffer);
  view.setUint32(0, options.badMagic ? 0 : 0x30534650, true);
  view.setUint32(4, options.badCount ?? names.length, true);
  view.setUint32(8, strs.length, true);
  let strOff = 0;
  names.forEach((name, i) => {
    const o = 16 + i*24;
    view.setBigUint64(o, 0n, true);
    view.setBigUint64(o+8, BigInt(options.oversized ? 9999999999 : 2), true);
    view.setUint32(o+16, strOff, true);
    strOff += new TextEncoder().encode(name).length + 1;
  });
  bytes.set(strs, 16+names.length*24);
  const reads = [];
  const file = {
    name: options.filename || gameNames[kind],
    size: options.size || 5_611_009_601,
    slice(start, end) {
      reads.push([start, end]);
      return new Blob([bytes.slice(start, end)]);
    }
  };
  return {file,reads};
}
async function main() {
  for(const kind of ["base","update"]) {
    const {file,reads}=fixture(kind);
    const x=await inspectNsp(file,kind);
    assert.equal(x.labelsMatch,true);
    assert.equal(x.entries,2);
    assert.equal(x.nca,2);
    assert.equal(x.title,kind==="base"?"0100000000010000":"0100000000010800");
    assert.equal(reads.length,2);
    assert.ok(reads.every(([a,b])=>b-a <= 16 * 1024 * 1024));
    assert.ok(reads.every(([a,b])=>a>=0&&b<2000));
  }
  assert.equal(identifyName("Odyssey.nsp","base").labelsMatch,false);
  assert.throws(()=>identifyName(gameNames.update,"base"),/Wrong base title ID/);
  const invalid = [
    ["not NSP", {filename:"archive.zip"},/\.nsp files only/],
    ["bad magic", {badMagic:true},/Not a standard PFS0/],
    ["count overflow", {badCount:100000},/Unexpected NSP file count/],
    ["entries outside file",{oversized:true},/outside the file/],
    ["no NCA",{noNca:true},/No NCA files/],
    ["wrong update version", {filename:"Odyssey [0100000000010800][v0].nsp"},/Wrong update NSP version/],
  ];
  for(const [label,opt,pattern] of invalid) {
    await assert.rejects(inspectNsp(fixture("update",opt).file,"update"),pattern,label);
  }
  console.log("Odyssey iPhone-only NSP PFS0 preflight: all synthetic tests passed");
}
await main();
