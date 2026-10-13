import { chromium } from "playwright";
const url = process.argv[2];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "fr-FR", viewport: { width: 1366, height: 900 } });
page.on("request", (r) => { const t = r.resourceType(); if (t === "xhr" || t === "fetch" || t==="document") console.log(r.method(), r.url().slice(0, 400), (r.postData()||"").slice(0,300)); });
await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(9000);
await browser.close();
