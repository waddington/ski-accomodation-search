import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB" });
const results = [];
page.on("request", (r) => { if (/Search\/rentals/.test(r.url())) console.log("REQ", r.method(), r.url(), r.postData()); });
page.on("response", async (r) => { if (/Search\/rentals/.test(r.url())) { try { results.push(await r.json()); } catch {} } });
await page.goto(process.argv[2], { waitUntil: "networkidle" });
await page.waitForTimeout(4000);
for (const j of results) { console.log("TOTAL", j.totalResults, j.heading); for (const p of j.properties || []) console.log(JSON.stringify(p).slice(0, 700)); }
await browser.close();
