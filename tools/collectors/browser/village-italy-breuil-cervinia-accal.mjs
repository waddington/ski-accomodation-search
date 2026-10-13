import { chromium } from "playwright";
const url = process.argv[2];
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB" });
await page.goto(url, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(2500);
for (let i = 0; i < (Number(process.argv[3]||1)); i++) {
  await page.locator("a.calendar-next").first().click().catch(e=>console.log('noclick',e.message));
  await page.waitForTimeout(3000);
}
const out = await page.$$eval("table", ts => ts.map(t => {
  const cap = (t.closest('div')?.innerText||'').split('\n')[0];
  const days = [...t.querySelectorAll('td')].map(td => `${td.innerText.trim()}:${td.className}`).filter(s=>!s.startsWith(':'));
  return cap + ' | ' + days.join(' ');
}));
console.log(out.join('\n'));
await browser.close();
