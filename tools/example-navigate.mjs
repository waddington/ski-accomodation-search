// Template for interactive scraping: search, click through, paginate.
// Copy to tools/scratch/<name>.mjs (must live under tools/ so `playwright` resolves), edit, then:
//   node tools/scratch/<name>.mjs
import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true, channel: "chrome" }); // system Chrome
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
await page.goto("https://www.allchalets.com/", { waitUntil: "domcontentloaded" });

// cookie banner
await page.getByRole("button", { name: /accept/i }).first().click().catch(() => {});

// type a search and submit
// await page.getByPlaceholder(/resort|where/i).fill("Les Coches");
// await page.keyboard.press("Enter");
// await page.waitForLoadState("networkidle");

// collect listings across pages
const results = [];
for (let p = 1; p <= 20; p++) {
  const cards = await page.$$eval("a[href*='/chalet']", (as) =>
    as.map((a) => ({ href: a.href, text: a.innerText.trim().replace(/\s+/g, " ").slice(0, 200) }))
  );
  results.push(...cards);
  const next = page.getByRole("link", { name: /next|›|»/i }).first();
  if (!(await next.count())) break;
  await next.click();
  await page.waitForLoadState("networkidle");
}
console.log(JSON.stringify([...new Map(results.map((r) => [r.href, r])).values()], null, 2));
await browser.close();
