import { chromium } from "playwright";
const url = process.argv[2];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(4000);
await page.getByRole("button", { name: /accept/i }).first().click().catch(() => {});
const tabs = await page.$$("a.select-month");
for (const t of tabs) {
  const txt = (await t.innerText()).trim();
  if (txt !== "March") continue;
  const id = await t.getAttribute("id");
  await t.evaluate((el) => el.click());
  await page.waitForTimeout(2500);
  // find the enclosing price container
  const block = await t.evaluate((el) => {
    let p = el; for (let i = 0; i < 8 && p; i++) { p = p.parentElement; if (p && /SATURDAY|SUNDAY/i.test(p.innerText) ) break; }
    return p ? p.innerText.replace(/\s+/g, " ") : "";
  });
  console.log("== tab", id, "\n", block.slice(0, 1500));
}
await browser.close();
