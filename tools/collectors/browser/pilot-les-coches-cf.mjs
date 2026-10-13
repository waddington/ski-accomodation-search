import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB" });
page.on("response", async (r) => {
  const u = r.url(); const ct = r.headers()["content-type"] || "";
  if (ct.includes("json")) { let b=""; try { b = (await r.text()); } catch {} console.log("XHR", u, b.length, b.slice(0, 400).replace(/\n/g," ")); }
});
await page.goto(process.argv[2], { waitUntil: "networkidle" });
await page.waitForTimeout(3000);
await browser.close();
