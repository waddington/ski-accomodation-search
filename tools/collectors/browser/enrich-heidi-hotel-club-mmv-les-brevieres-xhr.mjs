import { chromium } from "playwright";
const url = "https://www.mmv-holidays.co.uk/destinations/northern-french-alps/tignes/holiday-village-brevieres-winter";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
const reqs = [];
page.on("response", async r => {
  const t = r.request().resourceType();
  if (t === "xhr" || t === "fetch") {
    let body = ""; try { body = (await r.text()).slice(0, 300); } catch {}
    reqs.push(`${r.request().method()} ${r.url().slice(0,250)}\n    ${body.replace(/\s+/g,' ')}`);
  }
});
await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(3000);
await page.getByRole("button", { name: /accept|accepter/i }).first().click().catch(()=>{});
await page.waitForTimeout(1500);
await page.getByText("Arrival", { exact: true }).first().click().catch(e=>console.log("arr", e.message));
await page.waitForTimeout(3000);
await page.screenshot({ path: process.argv[2] + "/cal.png" });
console.log(reqs.filter(r=>!/google|doubleclick|facebook|criteo|analytics|hotjar|didomi|tiktok|bing|pinterest/i.test(r)).join("\n"));
await browser.close();
