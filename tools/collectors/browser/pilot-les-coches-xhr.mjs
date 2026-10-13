import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
page.on("response", async (r) => { const ct = r.headers()["content-type"] || ""; const u=r.url(); if ((ct.includes("json")||ct.includes("html")) && r.request().resourceType().match(/xhr|fetch/)) { let b=""; try{b=await r.text();}catch{} console.log("XHR", r.request().method(), u.slice(0,250), b.length, b.slice(0,300).replace(/\s+/g," ")); if (r.request().postData()) console.log("   POST", r.request().postData().slice(0,500)); } });
await page.goto(process.argv[2], { waitUntil: "networkidle" }).catch(()=>{});
await page.getByRole("button", { name: /accept|agree|ok/i }).first().click({ timeout: 3000 }).catch(() => {});
for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 2500); await page.waitForTimeout(700); }
await page.waitForTimeout(3000);
const t = await page.evaluate(() => document.body.innerText);
console.log("TEXTLEN", t.length);
require_out: {
  const fs = await import("fs"); fs.writeFileSync(process.argv[3], t);
}
await browser.close();
