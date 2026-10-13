import { chromium } from "playwright";
import fs from "fs";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "fr-FR", viewport: { width: 1366, height: 900 } });
await page.goto(process.argv[2], { waitUntil: "networkidle" }).catch(() => {});
await page.waitForTimeout(4000);
await page.locator("text=Accepter & Fermer").first().click().catch(()=>{});
for (let i = 0; i < 15; i++) { await page.mouse.wheel(0, 2500); await page.waitForTimeout(1200); }
const cards = await page.$$eval('a[href*="/fr/product/"]', as => [...new Set(as.map(a => a.href))].map(h => { const a=[...document.querySelectorAll(`a[href="${new URL(h).pathname + new URL(h).search}"], a[href="${h}"]`)][0]; let c=a; for(let i=0;i<8&&c.parentElement;i++){ c=c.parentElement; if(c.innerText.includes('voyageurs')&&c.innerText.includes('€')) break;} return {h, t:c.innerText.replace(/\s+/g,' ').slice(0,400)}; }));
fs.writeFileSync(process.argv[3], JSON.stringify(cards, null, 1));
console.log(cards.length);
await browser.close();
