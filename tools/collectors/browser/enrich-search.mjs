import { chromium } from "playwright";
const q = process.argv[2];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB" });
await page.goto("https://www.bing.com/search?q=" + encodeURIComponent(q), { waitUntil: "domcontentloaded" });
await page.waitForTimeout(2500);
const r = await page.$$eval("li.b_algo", ls => ls.map(l => (l.querySelector("h2 a")?.href||'') + "\n   " + (l.innerText||'').replace(/\s+/g,' ').slice(0,250)));
console.log(r.join("\n") || (await page.innerText("body")).slice(0,800));
await browser.close();
