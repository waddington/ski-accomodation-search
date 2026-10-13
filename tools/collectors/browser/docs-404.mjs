import { chromium } from "playwright";
const b = await chromium.launch({ headless: true, channel: "chrome" });
const p = await b.newPage();
const bad = new Set(); p.on("response", r => r.status() >= 400 && bad.add(r.url().replace(/\?t=\d+/, "")));
await p.goto("http://localhost:8791/"); await p.waitForTimeout(4000);
console.log([...bad].slice(0, 12).join("\n"), "\n", bad.size, "failed; cards:", await p.$$eval(".card", c => c.length));
await b.close();
