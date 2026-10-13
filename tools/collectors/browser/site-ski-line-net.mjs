import { chromium } from "playwright";
import fs from "fs";
const url = process.argv[2]; const out = process.argv[3];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
const log = [];
page.on("response", async (r) => {
  const t = r.request().resourceType();
  if (t === "xhr" || t === "fetch") {
    let body = ""; try { body = (await r.text()).slice(0, 4000); } catch {}
    log.push({ url: r.url(), method: r.request().method(), post: r.request().postData(), status: r.status(), body });
  }
});
await page.goto(url, { waitUntil: "networkidle", timeout: 60000 }).catch(()=>{});
await page.waitForTimeout(3000);
fs.writeFileSync(out, JSON.stringify(log, null, 1));
await browser.close();
