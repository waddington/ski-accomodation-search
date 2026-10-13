import { chromium } from "playwright";
const url = process.argv[2];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
page.on("response", async r => {
  const t = r.request().resourceType();
  if (t === "xhr" || t === "fetch") {
    let body = ""; try { body = (await r.text()).slice(0, 300); } catch {}
    console.log(r.request().method(), r.status(), r.url().slice(0, 300), "\n   POST:", (r.request().postData() || "").slice(0, 400), "\n   BODY:", body.replace(/\s+/g, " "));
  }
});
await page.goto(url, { waitUntil: "networkidle" }).catch(() => {});
await page.waitForTimeout(5000);
await browser.close();
