import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "fr-FR" });
for (const cat of process.argv.slice(2)) {
  await page.goto("https://www.tignes.net/guide-station/annuaire/hebergements/" + cat, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3000);
  await page.getByRole("button", { name: /accepter|tout accepter|accept/i }).first().click().catch(()=>{});
  for (let i = 0; i < 15; i++) {
    const more = page.getByText(/voir plus de résultats/i).first();
    if (!(await more.isVisible().catch(()=>false))) break;
    await more.click().catch(()=>{}); await page.waitForTimeout(2500);
  }
  const links = await page.$$eval("a", as => as.map(a => a.href).filter(h => /annuaire\/hebergements\/[^/]+\/[^/?#]+$/.test(h)));
  console.log("== " + cat + " " + new Set(links).size);
  console.log([...new Set(links)].join("\n"));
  await page.waitForTimeout(2500);
}
await browser.close();
