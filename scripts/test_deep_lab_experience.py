#!/usr/bin/env python3
"""Bounded checks for deep proofs, precise boundary states, gallery and layout."""

from project_paths import use_project_root, launch_browser
use_project_root()
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/五册教材教参整合'
DEST=OUT/'deep-verification'
FAMILIES=('deep-geometry','deep-analysis','deep-spatial')
CHECKS=[]
def check(name,value):
    if not value: raise AssertionError(name)
    CHECKS.append(name)
def main():
    DEST.mkdir(exist_ok=True)
    specs=[a for f in FAMILIES for a in json.loads((ROOT/f'scripts/textbook-labs/{f}.json').read_text(encoding='utf-8'))['assets']]
    errors=[]; reviews={}
    with sync_playwright() as p:
        browser=launch_browser(p, headless=True)
        for a in specs:
            page=browser.new_page(viewport={'width':1100,'height':900})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.route('http://**/*',lambda r:r.abort()); page.route('https://**/*',lambda r:r.abort())
            source=ROOT/f'scripts/visual-assets/textbook-{a["id"]}.html'
            page.goto(source.as_uri())
            check(a['id']+': pure model ready',page.evaluate('window.__textbookLab.id')==a['id'])
            page.screenshot(path=str(DEST/f'{a["id"]}-desktop.png'),full_page=True)
            page.locator('.lab-proof>summary').click()
            check(a['id']+': proof really rendered',page.locator('.lab-proof math').count()>0 and page.locator('.lab-proof').evaluate('el=>el.open'))
            for m in page.locator('.lab-proof math').all():
                check(a['id']+': MathML has visible extent',m.bounding_box()['height']>8)
            page.set_viewport_size({'width':390,'height':844})
            check(a['id']+': expanded proof fits mobile width',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            page.screenshot(path=str(DEST/f'{a["id"]}-mobile-proof.png'),full_page=True)
            page.locator('.lab-proof>summary').click()
            page.screenshot(path=str(DEST/f'{a["id"]}-mobile.png'),full_page=True)
            # Default labels must remain inside the mathematical viewBox.
            bounds=page.locator('#diagram text').evaluate_all('els=>els.map(e=>({text:e.textContent,...(()=>{let b=e.getBBox();return {x:b.x,y:b.y,w:b.width,h:b.height}})()}))')
            check(a['id']+': diagram labels inside canvas',all(b['x']>=-1 and b['x']+b['w']<=601 and b['y']>=-1 and b['y']+b['h']<=361 for b in bounds))
            initial=a['initial']; sid=a['id']
            if sid=='chord-midpoint-domain':
                for u,k in [(-1,'tangent'),(1,'tangent'),(1.05,'outside'),(.95,'secant')]:
                    page.evaluate('s=>TixuPlugin.setState(s)',{**initial,'u':u});check(sid+f': boundary {u}',page.evaluate('__textbookLab.model.kind')==k)
            if sid=='line-plane-minimum-angle':
                page.evaluate('s=>TixuPlugin.setState(s)',{**initial,'theta':90});check(sid+': perpendicular degenerate projection',page.evaluate('__textbookLab.model.allMinimum') is True)
            if sid=='ssa-circle-ray':
                for angle,count in [(30,1),(90,0),(120,0)]:
                    page.evaluate('s=>TixuPlugin.setState(s)',{**initial,'A':angle,'mode':'height'});check(sid+f': tangent ray {angle}',page.evaluate('__textbookLab.model.count')==count)
            if sid=='parameter-cubic-roots':
                for value,count in [(-2,2),(-1.95,3),(-2.05,1),(2,2)]:
                    page.evaluate('s=>TixuPlugin.setState(s)',{**initial,'a':value});check(sid+f': roots {value}',page.evaluate('__textbookLab.model.count')==count)
            if sid=='cube-plane-transitions':
                for offset,count in [(6,3),(4,4),(2,5),(0,6),(9,1),(10,0)]:
                    page.evaluate('s=>TixuPlugin.setState(s)',{**initial,'offset':offset});check(sid+f': cross section {offset}',page.evaluate('__textbookLab.model.points.length')==count)
            # A representative critical-state image supplements default-state review.
            page.screenshot(path=str(DEST/f'{sid}-boundary.png'),full_page=True)
            page.close()
        page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((OUT/'deep-index.html').as_uri())
        check('gallery has seven choices',page.locator('[data-index]').count()==7)
        for i,a in enumerate([next(s for s in specs if s['id']==x) for x in ('chord-midpoint-domain','parameter-cubic-roots','line-plane-minimum-angle','counting-equal-multiplicity','bayes-base-rate','ssa-circle-ray','cube-plane-transitions')]):
            page.locator(f'[data-index="{i}"]').click()
            page.wait_for_function('(id)=>document.querySelector("#experiment").title===id',arg=a['title'])
            frame=page.locator('#experiment').element_handle().content_frame()
            frame.wait_for_function('Boolean(window.__textbookLab)')
            check(a['id']+': one active gallery iframe',page.locator('iframe').count()==1 and frame.evaluate('__textbookLab.id')==a['id'])
        page.locator('[data-index="0"]').click();page.wait_for_timeout(200)
        page.screenshot(path=str(DEST/'gallery-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200)
        check('gallery fits mobile width',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
        page.screenshot(path=str(DEST/'gallery-mobile.png'),full_page=True)
        for a in specs:
            p=a['placements'][0];sid=p['sectionId'];page.goto((OUT/sid.split('-')[0]/sid/'teacher.html').as_uri())
            page.wait_for_function('document.documentElement.dataset.visualReady === "true"')
            frame=next(f for f in page.frames if f!=page.main_frame and f.evaluate('window.LAB_SPEC?.id||null')==a['id'])
            frame.wait_for_function('Boolean(window.__textbookLab)')
            frame.locator('.lab-proof>summary').click();page.wait_for_timeout(400)
            check(a['id']+': chapter expanded proof iframe resizes',frame.locator('main').evaluate('e=>e.getBoundingClientRect().height') <= frame.frame_element().evaluate('e=>e.clientHeight')+1)
        browser.close()
    check('no unhandled browser exceptions',not errors)
    result={'status':'passed','checks':len(CHECKS),'checksDetail':CHECKS,'errors':errors,'checkedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'screenshots':str(DEST),'limitations':['截图不等于真实触摸设备测试。','打印沿用正文完整内容与代表状态静态图，不把交互图当作证明。']}
    (DEST/'experience-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','checks','errors')},ensure_ascii=False));print(DEST)
if __name__=='__main__':main()
