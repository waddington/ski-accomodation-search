import { chromium } from "playwright";
const [arr, dep, out] = process.argv.slice(2);
const url = "https://www.mmv-holidays.co.uk/destinations/northern-french-alps/tignes/holiday-village-brevieres-winter";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
const reqs = [];
page.on("request", r => { if (/mmv/.test(r.url()) && ["xhr","fetch","document"].includes(r.resourceType())) reqs.push(r.method()+" "+r.url().slice(0,300)); });
await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(3000);
await page.getByRole("button", { name: /accept|accepter/i }).first().click().catch(()=>{});
await page.waitForTimeout(1000);
await page.evaluate(([a,d]) => {
  document.querySelector("#establishment-arrival-input").value = a;
  document.querySelector("#establishment-departure-input").value = d;
  document.querySelector("input[name=adults]").value = "8";
  const f = document.querySelector("#establishment-search-form");
  f.requestSubmit ? f.requestSubmit() : f.submit();
}, [arr, dep]);
await page.waitForTimeout(8000);
console.log("URL:", page.url());
console.log(reqs.join("\n"));
await page.screenshot({ path: out + "/after.png", fullPage: false });
const txt = await page.innerText("body"); 
require_fs: { const fs = await import("fs"); fs.writeFileSync(out + "/after.txt", txt); }
await browser.close();
