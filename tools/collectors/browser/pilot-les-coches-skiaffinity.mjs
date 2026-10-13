import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB" });
await page.goto("https://www.skiaffinity.com/chalet-jessica-paradiski", { waitUntil: "networkidle" });
for (const v of ["07/02/2027", "07/03/2027", "04/04/2027"]) {
  await page.selectOption("select.monthPicker", v);
  await page.waitForTimeout(3500);
  await page.waitForLoadState("networkidle").catch(() => {});
  const t = await page.$$eval(".block.prices li", (ls) => ls.map((l) => l.innerText.replace(/\s+/g, " ").trim()));
  console.log(v, JSON.stringify(t));
}
await browser.close();
