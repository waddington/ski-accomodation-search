import { chromium } from "playwright";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({ locale: "en-GB", viewport: { width: 1366, height: 900 } });
const xhr=[];
page.on('response', async r=>{ const u=r.url(); if(/json|api|Avail|Rate|Search/i.test(u) && !/\.(js|css|png|svg|woff)/.test(u)) xhr.push(u.slice(0,200)); });
await page.goto(process.argv[2], { waitUntil: "networkidle" });
await page.waitForTimeout(3000);
for (let i=0;i<5;i++){ await page.locator('text=zbe_chevron_right').first().click().catch(()=>{}); await page.waitForTimeout(500);}
const txt = await page.innerText('body');
const m = txt.indexOf('March 2027'); console.log('march idx', m);
// click day 20 then 27 within March block
const days = page.locator('xpath=//*[normalize-space(text())="20"]');
console.log('count20', await days.count());
await page.screenshot({path: process.argv[3]+'/cal.png'});
console.log(xhr.join('\n'));
await browser.close();
