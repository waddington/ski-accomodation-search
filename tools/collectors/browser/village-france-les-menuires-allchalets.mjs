import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
const out = new Map();
for (const url of process.argv.slice(2)) {
  await page.goto(url, { waitUntil: "networkidle" }).catch(() => {});
  await page.getByRole("button", { name: /accept/i }).first().click({ timeout: 3000 }).catch(() => {});
  for (let p = 1; p <= 15; p++) {
    for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, 3000); await page.waitForTimeout(500); }
    const cards = await page.$$eval("a[href*='/holiday-rentals/']", (as) => as.map((a) => {
      let c = a; for (let k = 0; k < 6 && c.parentElement && c.innerText.length < 80; k++) c = c.parentElement;
      return { href: a.href.split("?")[0], text: c.innerText.replace(/\s+/g, " ").slice(0, 300) };
    }));
    let added = 0;
    for (const c of cards) { const o = out.get(c.href); if (!o || (o.text.length < c.text.length)) { if (!o) added++; out.set(c.href, { ...c, src: url }); } }
    console.error(url, "page", p, "cards", cards.length, "new", added);
    const next = page.locator("a[rel=next], a:has-text('Next'), button:has-text('Next'), a[aria-label*='next' i], button:has-text('Load more'), button:has-text('Show more')").first();
    if (!(await next.count()) || !(await next.isVisible().catch(() => false))) break;
    await next.click().catch(() => {}); await page.waitForTimeout(3000); await page.waitForLoadState("networkidle").catch(() => {});
    if (added === 0 && p > 1) break;
  }
  await page.waitForTimeout(2000);
}
console.log(JSON.stringify([...out.values()], null, 1));
await browser.close();
