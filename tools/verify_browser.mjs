import puppeteer from 'puppeteer';
import fs from 'node:fs/promises';
import {execFileSync, spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root=fileURLToPath(new URL('../',import.meta.url));
const args=process.argv.slice(2);
if(args.length && (args.length!==2 || args[0]!=='--url'))throw new Error('Usage: node tools/verify_browser.mjs [--url HTTPS_ORIGIN]');
const live=args.length===2;
const output=path.join(root,'build/browser-check',live?'live':'local');
await fs.mkdir(output,{recursive:true});
const receiptPath=path.join(output,'results.json');
await fs.writeFile(receiptPath,JSON.stringify({status:'RUNNING'}));
let server,browser;
try{
  let origin;
  if(live){
    const url=new URL(args[1]);
    if(url.protocol!=='https:' || url.pathname!=='/' || url.search || url.hash)throw new Error('--url must be an HTTPS origin');
    origin=url.origin;
  }else{
    const site=execFileSync('python3',['tools/blog.py','artifact'],{cwd:root,encoding:'utf8'}).trim();
    server=spawn('python3',['-u','-m','http.server','0','--bind','127.0.0.1','--directory',site],{stdio:['ignore','pipe','pipe']});
    const port=await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('Preview startup timeout')),5000);
      server.once('error',reject);
      server.stdout.on('data',data=>{const match=data.toString().match(/port (\d+)/);if(match){clearTimeout(timer);resolve(match[1]);}});
      server.once('exit',code=>reject(new Error('Preview exited '+code)));
    });
    origin='http://127.0.0.1:'+port;
  }
  browser=await puppeteer.launch({headless:true,args:process.env.BROWSER_NO_SANDBOX==='1'?['--no-sandbox']:[]});
  const page=await browser.newPage();
  if(!live){
    await page.setRequestInterception(true);
    page.on('request',request=>request.url().startsWith(origin+'/')||request.url().startsWith('data:')?request.continue():request.abort());
  }
  const response=await page.goto(origin+'/',{waitUntil:'domcontentloaded',timeout:45000});
  if(response.status()!==200)throw new Error('Home HTTP '+response.status());
  const home=await page.evaluate(()=>({title:document.title,heading:document.querySelector('.hero h1').innerText,cards:document.querySelectorAll('.post-card').length,count:Number.parseInt(document.querySelector('.post-count').innerText,10),dates:[...document.querySelectorAll('.post-card time')].map(node=>node.getAttribute('datetime'))}));
  if(!home.title || !home.heading || !home.cards || home.cards!==home.count || home.dates.some((date,index)=>index && date>home.dates[index-1]))throw new Error('Homepage/count/order mismatch');
  const viewports=[];
  for(const width of [1280,390,320]){
    await page.setViewport({width,height:900});
    const dimensions=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
    if(dimensions.scroll>width)throw new Error('Horizontal overflow: '+JSON.stringify(dimensions));
    viewports.push(dimensions);
    await page.screenshot({path:path.join(output,'home-'+width+'.png')});
  }
  const seriesLink=await page.$('.post-card .series-tag a');
  let series=null;
  if(seriesLink){
    const expected=await seriesLink.evaluate(node=>({href:node.getAttribute('href'),title:node.textContent}));
    await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),seriesLink.click()]);
    series=await page.evaluate(()=>({path:location.pathname,title:document.querySelector('h1').innerText,rows:[...document.querySelectorAll('li[data-order]')].map(node=>({order:Number(node.dataset.order),status:node.dataset.status}))}));
    if(series.path!==expected.href || series.title!==expected.title || new Set(series.rows.map(row=>row.order)).size!==series.rows.length)throw new Error('Series navigation/duplicate order mismatch');
    await page.setViewport({width:390,height:900});
    await page.screenshot({path:path.join(output,'series-mobile.png')});
    await page.goto(origin+'/',{waitUntil:'domcontentloaded'});
  }
  const topicLink=await page.$('.post-card .tag-list li:not(.series-tag) a');
  let topic=null;
  if(topicLink){
    const expected=await topicLink.evaluate(node=>node.textContent);
    await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),topicLink.click()]);
    topic=await page.evaluate(()=>({path:location.pathname,title:document.querySelector('h1').innerText,count:document.querySelectorAll('.post-card').length}));
    if(topic.title!==expected || !topic.count)throw new Error('Topic navigation mismatch');
    await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.click('.post-card h2 a')]);
  }else{
    await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.click('.post-card h3 a')]);
  }
  const article=await page.evaluate(()=>({path:location.pathname,title:document.title,ga:document.querySelectorAll('script[src*="googletagmanager.com/gtag/js"]').length,giscus:document.querySelectorAll('script[src*="giscus.app/client.js"]').length,mapping:document.querySelector('script[src*="giscus.app/client.js"]')?.getAttribute('data-mapping')}));
  if(article.ga!==1 || article.giscus!==1 || article.mapping!=='pathname')throw new Error('Analytics/comment integration mismatch');
  if(live)await page.waitForFunction(()=>Boolean(document.querySelector('iframe.giscus-frame')),{timeout:25000});
  const result={status:'PASS',origin,home,viewports,series,topic,article};
  await fs.writeFile(receiptPath,JSON.stringify(result,null,2));
  console.log(JSON.stringify(result,null,2));
}catch(error){
  await fs.writeFile(receiptPath,JSON.stringify({status:'FAIL',error:String(error)},null,2));
  throw error;
}finally{
  if(browser)await browser.close();
  if(server)server.kill('SIGTERM');
}
