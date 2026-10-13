import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "fr-FR", viewport: { width: 1366, height: 900 } });
page.on("request", r => { const u = r.url(); if (/booking|ajax|search|result/i.test(u) && !/\.(js|css|png|jpg|svg|woff)/.test(u)) console.error("REQ", r.method(), u.slice(0, 400), (r.postData()||"").slice(0,400)); });
await page.goto("https://fr.locationlesmenuires.com/appartements-residences-chalets.html", { waitUntil: "networkidle" }).catch(() => {});
await page.waitForTimeout(3000);
await page.evaluate(() => {
  const f = document.querySelector("form.form-recherche");
  f.querySelector("input[name=datedeb]").value = "20/03/2027";
  f.querySelector("input[name=datefin]").value = "27/03/2027";
  f.querySelector("input[name=adultes]").value = "8";
});
await page.locator("form.form-recherche input.form_search").first().click({ force: true }).catch(e => console.error("click", e.message));
await page.waitForTimeout(10000);
console.log(page.url());
const txt = await page.innerText("body");
console.log(txt.slice(0, 6000));
await browser.close();
