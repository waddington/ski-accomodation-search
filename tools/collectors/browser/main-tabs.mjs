import { chromium } from "playwright";
const url = process.argv[2];
const b = await chromium.launch({ headless: true, channel: "chrome" });
const p = await b.newPage();
await p.goto(url, { waitUntil: "domcontentloaded" });
await p.waitForTimeout(3000);
let out = "";
for (const name of ["HIGHLIGHTS", "DESCRIPTION", "WHAT'S INCLUDED", "ADDITIONAL SERVICES", "ROOMS & FLOORPLAN"]) {
  const t = p.getByText(name, { exact: true }).first();
  if (await t.count()) { await t.click().catch(() => {}); await p.waitForTimeout(1500); out += `\n=== ${name}\n` + (await p.evaluate(() => document.body.innerText)); }
}
console.log(out);
await b.close();
