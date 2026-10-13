import { chromium } from "playwright";
const url = process.argv[2];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
await page.goto(url, { waitUntil: "networkidle" }).catch(() => {});
await page.waitForTimeout(4000);
const out = new Map();
for (let p = 1; p <= 6; p++) {
  for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 2500); await page.waitForTimeout(400); }
  const cards = await page.$$eval("a[href*='/product-']", as => as.map(a => {
    let c = a; for (let k = 0; k < 8 && c.parentElement && c.innerText.length < 120; k++) c = c.parentElement;
    return { href: a.href.split("#")[0], text: c.innerText.replace(/\s+/g, " ").slice(0, 400) };
  }));
  let added = 0;
  for (const c of cards) if (!out.has(c.href)) { out.set(c.href, c); added++; }
  console.error("page", p, "cards", cards.length, "new", added);
  const next = page.locator(".pagination a:has-text('›'), .pagination a:has-text('Next'), a[rel=next], li.next a, a:has-text('Next page'), button:has-text('Load more'), button:has-text('See more'), a:has-text('See more results')").first();
  if (!(await next.count())) { console.error("no next"); break; }
  await next.click().catch(e => console.error("click fail", e.message));
  await page.waitForTimeout(5000);
  if (added === 0 && p > 1) break;
}
console.log(JSON.stringify([...out.values()], null, 1));
await browser.close();
