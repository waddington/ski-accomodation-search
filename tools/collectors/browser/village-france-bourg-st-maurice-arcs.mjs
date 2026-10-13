import { chromium } from 'playwright';
const b = await chromium.launch({channel:'chrome'}); const p = await b.newPage();
p.on('request', r => { const t=r.resourceType(); if ((t==='xhr'||t==='fetch') && r.url().includes('lesarcs-reservation.com')) console.log('REQ', r.method(), r.url(), (r.postData()||'').slice(0,2500)); });
await p.goto('https://www.lesarcs-reservation.com/location-appartements-et-studios-aux-arcs', {waitUntil:'networkidle', timeout:60000});
await p.waitForTimeout(1500);
for (const t of ['Tri par station']) { try { await p.getByText(t).first().click({timeout:4000}); } catch(e){ console.log('noclick',t); } }
await p.waitForTimeout(1000);
console.log('labels', await p.locator('label[for="village-10"]').count());
try { await p.locator('label[for="village-10"]').first().click({timeout:4000}); } catch(e) { console.log('err', e.message.slice(0,80)); await p.evaluate(()=>{const e=document.getElementById('village-10'); if(e){e.click();}}); }
await p.waitForTimeout(5000);
const txt = await p.locator('body').innerText(); const m = txt.match(/\d+ résultats/g); console.log('COUNT', m && m.slice(0,4));
await b.close();
