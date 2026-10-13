import { chromium } from 'playwright';
const b = await chromium.launch({channel:'chrome'}); const p = await b.newPage();
p.on('request', r => { const t=r.resourceType(); if (t==='xhr'||t==='fetch') { if (r.url().includes(process.env.MATCH||'api.openbooking')) console.log('REQ', r.method(), r.url(), (r.postData()||'').slice(0,800)) }; });
await p.goto(process.argv[2], {waitUntil:'networkidle', timeout:60000});
await p.waitForTimeout(3000);
await b.close();
