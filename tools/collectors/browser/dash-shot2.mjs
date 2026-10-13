import { chromium } from "playwright";
const b = await chromium.launch({ headless: true, channel: "chrome" });
const p = await b.newPage({ viewport: { width: 1300, height: 1100 } });
const errs = []; p.on("pageerror", e => errs.push(e.message)); p.on("console", m => m.type() === "error" && !m.text().includes("404") && errs.push(m.text()));
await p.goto("http://localhost:8777/"); await p.waitForTimeout(3000);
const chart = await p.$("#chart"); await chart.scrollIntoViewIfNeeded();
const box = await chart.boundingBox(); await p.mouse.move(box.x + box.width * 0.5, box.y + 120); await p.waitForTimeout(300);
await p.screenshot({ path: process.argv[2], clip: { x: 0, y: Math.max(0, box.y - 420), width: 1300, height: 760 } });
// filters: tick "wrong size", max £ 800
await p.check('[data-rule="sleeps"]'); await p.fill('[data-f="maxpp"]', "800"); await p.dispatchEvent('[data-f="maxpp"]', "change");
await p.waitForTimeout(500);
const f = await p.$("#filters"); await f.scrollIntoViewIfNeeded();
const fb = await f.boundingBox();
await p.screenshot({ path: process.argv[3], clip: { x: 0, y: fb.y - 70, width: 1300, height: 760 } });
console.log("count:", await p.textContent("#count"), "now:", (await p.textContent("#now")).slice(0, 120));
console.log("errors:", errs);
await p.evaluate(() => localStorage.clear());
await b.close();
