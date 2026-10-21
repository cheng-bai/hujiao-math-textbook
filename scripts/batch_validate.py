#!/usr/bin/env python3
"""Sequential offline/print checks; a structure pass is not a mathematics review."""

from project_paths import use_project_root, launch_browser
use_project_root()
import argparse
import hashlib
import json
import re
import tempfile
import traceback
import zipfile
from pathlib import Path, PurePosixPath

import fitz
from playwright.sync_api import sync_playwright
from batch_render import OUTPUT, ROOT, VENDOR, output_dir, render_section, save_json, section_paths, sha, visual_files
from test_print import choose

VERSION = 'batch-validate-v1.5'
MATH_RE = re.compile(r'\$\$[\s\S]*?\$\$|(?<!\$)\$(?!\$)[^$\n]+\$')


def formula_count(blocks, student=False):
    texts = []
    for b in blocks:
        if student and (b.get('teacher_only') or b['type'] in ['intro', 'teacher', 'editor']):
            continue
        if b['type'] != 'heading':
            texts.append(b['markdown'])
        if b['type'] in ['heading', 'question', 'teacher', 'editor', 'intro']:
            texts.append(b.get('title', ''))
        if b['type'] == 'question' and not student:
            texts.extend([b['answer'], b['teacher_analysis']])
    return sum(len(MATH_RE.findall(t)) for t in texts)


def raw_table_count(blocks, student=False):
    total=0
    for b in blocks:
        if student and (b.get('teacher_only') or b['type'] in ['intro','teacher','editor']):
            continue
        fields=['markdown'] + (['answer','teacher_analysis'] if b['type']=='question' and not student else [])
        total+=sum(len(re.findall(r'<table\b',b.get(field,''),re.I)) for field in fields)
    return total


def has_answer_basis(question):
    if question.get('answer_provenance'):
        return True
    # Authored solutions cite the question and editorial evidence, never fake a teacher line.
    editorial = question.get('answer_editorial') or question.get('editorial_answer') or {}
    marked = '编辑' in question.get('answer', '')
    return marked and bool(question.get('provenance_question')) and (
        editorial.get('kind') == 'independently-derived' and bool(editorial.get('reason'))
        or editorial.get('status') == 'authored' and bool(editorial.get('basis'))
    )


def rendered_source_formula_count(page):
    # Condensed reading repeats selected key points; audit source math only once.
    return page.locator('.book-body').evaluate('''body => {
      const copy = body.cloneNode(true);
      copy.querySelectorAll('.visual-condensed').forEach(prose => {
        const original = prose.querySelector(':scope > .visual-original > .visual-original-body');
        if (original) prose.replaceChildren(...original.childNodes);
      });
      copy.querySelectorAll('.visual-module').forEach(el => el.remove());
      return copy.querySelectorAll('.katex').length;
    }''')


def ready(page, path):
    page.goto(Path(path).as_uri(), wait_until='load', timeout=30000)
    page.wait_for_function('document.documentElement.dataset.math !== undefined', timeout=15000)
    page.wait_for_function("document.documentElement.dataset.visualReady === 'true'", timeout=15000)
    page.wait_for_function("[...document.querySelectorAll('.book-body .visual-frame-status')].every(el=>el.hidden)", timeout=15000)
    page.evaluate('document.fonts.ready')


def markers(page):
    page.evaluate('''() => {
      window.paginationMarkers = false;
      addEventListener('beforeprint', () => {
        if (!window.paginationMarkers) return;
        document.querySelectorAll('#print-output .question').forEach((q, i) => {
          const leaves = [...q.querySelectorAll('p,li,h4,.question-label,.math.display')];
          for (const [suffix, host] of [['START', leaves[0]], ['END', leaves.at(-1)]]) {
            if (!host) continue;
            const marker = document.createElement('span');
            marker.textContent = `ZQ${String(i+1).padStart(4,'0')}${suffix}`;
            host.style.position = 'relative';
            marker.style.cssText = `position:absolute;left:0;${suffix==='START'?'top:2px':'bottom:2px'};font:2px/2px Arial;letter-spacing:0;white-space:nowrap`;
            host.append(marker);
          }
        });
      });
    }''')


def shared_regression(page, build, check):
    component_files = [ROOT / 'scripts/batch_render.py', ROOT / 'scripts/book.js', ROOT / 'scripts/book.css']
    if build.get('book_id') == 'x1':
        component_files.extend([ROOT / 'scripts/visual-book.js', ROOT / 'scripts/visual-book.css', ROOT / 'scripts/visual-assets/module-data.js', ROOT / 'scripts/visual-assets/ellipse-preview.png'])
    key = hashlib.sha256(('component-v3' + ''.join(sha(path) for path in component_files)).encode()).hexdigest()
    record = OUTPUT / '_component-validation.json'
    if record.exists() and json.loads(record.read_text(encoding='utf-8')).get('fingerprint') == key:
        check('shared_component_regression_cached', True)
        return
    original = page.locator('.book-body').inner_html()
    expected = page.locator('.book-body .question').count()
    checks = []
    for mode in ['all', 'text', 'questions', 'answers']:
        for category in [None, ['example'], ['practice'], ['homework']]:
            choose(page, mode, categories=category)
            count = 0 if mode == 'text' else page.locator('.book-body .question' + ('' if category is None else f'[data-category="{category[0]}"]')).count()
            okay = page.locator('#print-output .question').count() == count
            okay &= page.locator('#print-output .print-answer').count() == (count if mode in ['all', 'answers'] else 0)
            checks.append(bool(okay))
    modules = page.locator('.book-body .content-module').evaluate_all('(els)=>els.map(el=>el.dataset.module)')
    if modules:
        choose(page, 'questions', scopes=[modules[0]])
        selected = page.locator(f'.book-body [data-module="{modules[0]}"] .question').count()
        checks.append(page.locator('#print-output .question').count() == selected)
    choose(page, 'questions', scopes=[])
    checks.append(page.locator('#print-submit').is_disabled())
    checks.append(page.locator('.book-body').inner_html() == original)
    check('shared_component_modes_categories_scopes_and_dom', all(checks), {'combinations': len(checks), 'questions': expected})
    page.locator('#density-toggle').click()
    check('shared_density_toggle', page.locator('body.spacious').count() == 1)
    page.locator('#density-toggle').click()
    if expected:
        page.locator('#answer-toggle').click()
        check('shared_answer_toggle', page.locator('.answer:visible,.question-analysis:visible').count() == 0)
        page.locator('#answer-toggle').click()
    if all(checks):
        save_json(record, {'status': 'passed', 'fingerprint': key, 'checks': len(checks), 'tested_section': build['id'], 'scope': 'Shared print UI, categories, modules, empty scope, density and answer controls. Section-specific render/PDF checks are not cached by this record.'})


def print_pdf(page, out, mode, expected, check, warnings):
    choose(page, mode)
    check(f'{mode}_selected_question_count', page.locator('#print-output .question').count() == expected)
    normal = out / 'verification' / f'{mode}.pdf'
    page.pdf(path=str(normal), prefer_css_page_size=True, print_background=False)
    with fitz.open(normal) as doc:
        metadata = doc.metadata
        metadata['author'] = 'chengbai'
        doc.set_metadata(metadata)
        doc.saveIncr()
        texts = [p.get_text() for p in doc]
        check(f'{mode}_a4_and_no_blank_pages', all(abs(p.rect.width-595.3)<2 and abs(p.rect.height-841.9)<2 and bool(t.strip()) for p,t in zip(doc,texts)))
        outside = [i+1 for i,p in enumerate(doc) if any(w[0]<-1 or w[1]<-1 or w[2]>p.rect.width+1 or w[3]>p.rect.height+1 for w in p.get_text('words'))]
        check(f'{mode}_no_text_outside_paper', not outside, outside)
        if mode == 'questions':
            check('questions_pdf_excludes_answer_heading', '答案与解析' not in '\n'.join(texts))
        pages = len(doc)
        # Measure each question at the actual print text width, without changing the PDF DOM.
        page.emulate_media(media='print')
        layout = page.evaluate('''() => {
          const output = document.querySelector('#print-output');
          const previous = output.style.cssText; output.style.setProperty('width', '186mm', 'important');
          const heights = [...output.querySelectorAll('.question')].map(q=>q.getBoundingClientRect().height);
          const box=output.getBoundingClientRect();
          const overwide=[...output.querySelectorAll('.math.display,table')].filter(el=>el.scrollWidth>el.clientWidth+2||el.getBoundingClientRect().right>box.right+2).map(el=>({tag:el.tagName,width:Math.round(el.getBoundingClientRect().width),scrollWidth:el.scrollWidth,text:el.textContent.slice(0,120)}));
          output.style.cssText = previous; return {heights,overwide};
        }''')
        heights=layout['heights']
        if layout['overwide']:
            warnings.append({'code':'print-content-overwide','mode':mode,'items':layout['overwide'],'message':'Inspect these formulas/tables for paper-edge clipping; source content was not removed or silently scaled.'})
        # Reset the override: forcing screen here would make subsequent PDFs screen media.
        page.emulate_media(media='null')
        if expected:
            page.evaluate('window.paginationMarkers = true')
            diagnostic = out / 'verification' / f'{mode}-pagination.pdf'
            page.pdf(path=str(diagnostic), prefer_css_page_size=True, print_background=False)
            page.evaluate('window.paginationMarkers = false')
            with fitz.open(diagnostic) as marked:
                check(f'{mode}_markers_preserve_page_count', len(marked) == len(doc))
                def words(p):
                    return sorted((tuple(round(v,2) for v in w[:4]),w[4]) for w in p.get_text('words') if not re.search(r'ZQ\d{4}(START|END)', w[4]))
                check(f'{mode}_markers_preserve_content_coordinates', len(marked)==len(doc) and all(words(a)==words(b) for a,b in zip(doc,marked)))
                positions = {}
                for i,p in enumerate(marked,1):
                    for token in re.findall(r'ZQ\d{4}(?:START|END)',p.get_text()):
                        positions.setdefault(token,[]).append(i)
                pagination = []
                for i in range(expected):
                    start,end = positions.get(f'ZQ{i+1:04d}START',[]),positions.get(f'ZQ{i+1:04d}END',[])
                    check(f'{mode}_q{i+1}_markers_present',len(start)==len(end)==1)
                    split = start != end
                    long = heights[i] > (297-12-13)*96/25.4 - 4
                    if split and long:
                        warnings.append({'code':'long-question-continued','mode':mode,'question_index':i+1,'pages':start+end,'height_px':round(heights[i])})
                    elif split:
                        check(f'{mode}_q{i+1}_single_page_when_fits',False,{'start':start,'end':end,'height_px':heights[i]})
                    pagination.append({'question_index':i+1,'start':start,'end':end,'oversized':long})
        else:
            pagination=[]
    return {'file':str(normal.relative_to(out)),'pages':pages,'questions':expected,'pagination':pagination}


def validate_section(path, browser, force=False):
    build = render_section(path)
    out = Path(build['output'])
    version_key = hashlib.sha256((VERSION + sha(__file__) + build['fingerprint']).encode()).hexdigest()
    target = out / 'validation.json'
    if not force and target.exists():
        old = json.loads(target.read_text(encoding='utf-8'))
        if old.get('fingerprint') == version_key and old.get('status') == 'passed' and all((out / p['file']).is_file() for p in old.get('pdfs', [])):
            return {**old,'cached':True}
    (out / 'verification').mkdir(exist_ok=True)
    blocks = json.loads((out / 'content.json').read_text(encoding='utf-8'))
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    checks,errors,warnings,pdfs=[],[],[],[]
    report = {'schema_version':1,'id':build['id'],'version':VERSION,'fingerprint':version_key,'build_fingerprint':build['fingerprint'],'status':'failed','checks':checks,'errors':errors,'warnings':warnings,'pdfs':pdfs,'math_review':'separate','limits':['Offline Chrome and A4/100% PDF only; no mathematics proof review.','Single-page-fit questions checked with absolute-position markers; oversized questions may continue.']}
    def check(name, passed, detail=None):
        item={'name':name,'passed':bool(passed)}
        if detail is not None:
            item['detail']=detail
        checks.append(item)
        if not passed:
            errors.append(item)
    page = browser.new_page(viewport={'width':1440,'height':1000},offline=True,reduced_motion='reduce')
    javascript_errors=[]
    page.on('pageerror',lambda e:javascript_errors.append(str(e)))
    try:
        check('source_hashes_unchanged',all(Path(p).is_file() and sha(p)==expected for p,expected in build['source_hashes'].items()))
        blocked = [issue for issue in build['issues'] if isinstance(issue,dict) and issue.get('severity') in ['blocking','error','critical']]
        check('no_blocking_source_or_answer_issues',not blocked,blocked)
        warnings.extend(issue for issue in build['issues'] if issue not in blocked)
        check('copied_images_match_sources',all((out/ref).is_file() and sha(out/ref)==item['sha256'] and sha(item['source'])==item['sha256'] for ref,item in build['assets'].items()))
        questions=[b for b in blocks if b['type']=='question' and not b.get('teacher_only')]
        ids=[q['id'] for q in questions]
        check('question_ids_unique',len(ids)==len(set(ids)))
        check('question_answer_and_provenance_complete',all(q['markdown'].strip() and q['answer'].strip() and q['provenance_question'] and has_answer_basis(q) for q in questions))
        html=(out/'student.html').read_text(encoding='utf-8')
        check('student_html_physically_excludes_private_content',all(token not in html for token in ['class="answer"','teacher-only','question-analysis','_sources/','images/private-','href="teacher.html"','隐藏全部答案']))
        with zipfile.ZipFile(out/'student.zip') as archive:
            names=archive.namelist()
            check('student_zip_crc',archive.testzip() is None)
            allowed=set(['student.html','book.css','book.js','visual-book.css','visual-book.js',*build['student_images']])
            allowed.update('visual-assets/'+name for name in visual_files(data, True))
            allowed.update('vendor-katex/'+p.relative_to(VENDOR).as_posix() for p in VENDOR.rglob('*') if p.is_file())
            check('student_zip_allowlist',set(names)==allowed and len(names)==len(set(names)) and all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n and not n.startswith(('sources/','_sources/','content/','verification/','images/private-')) and not n.endswith('-teacher.js') and n!='visual-assets/module-data.js' for n in names))
            check('student_zip_has_no_parent_resource_paths','../' not in archive.read('student.html').decode())
        for student,name in [(False,'teacher.html'),(True,'student.html')]:
            ready(page,out/name)
            label='student' if student else 'teacher'
            expected_math=formula_count(blocks,student)
            actual_math = rendered_source_formula_count(page)
            check(label+'_formula_count_and_errors',actual_math==expected_math and not page.evaluate('window.__mathErrors'),{'expected':expected_math,'actual':actual_math,'errors':page.evaluate('window.__mathErrors')})
            check(label+'_all_images_loaded',page.evaluate('[...document.images].every(i=>i.complete&&i.naturalWidth>0)'))
            check(label+'_question_count',page.locator('.book-body .question').count()==len(questions))
            check(label+'_source_tables_rendered',page.locator('.book-body table').count()>=raw_table_count(blocks,student),{'source_tables':raw_table_count(blocks,student),'rendered_tables':page.locator('.book-body table').count()})
            check(label+'_no_visible_html_table_markup',not page.locator('.book-body').evaluate('(el)=>/<(?:table|thead|tbody|tr|td|th|br)\\b/i.test(el.textContent)'))
            escaped_dollars=page.locator('.book-body').evaluate(r'''(el)=>{const copy=el.cloneNode(true);copy.querySelectorAll('.math,.katex').forEach(n=>n.remove());return (copy.textContent.match(/\$/g)||[]).length}''')
            if escaped_dollars:
                warnings.append({'code':'visible-dollar-delimiters','edition':label,'count':escaped_dollars,'message':'Raw dollar signs remain outside rendered math; inspect source delimiters or intentional currency/escaping.'})
            if not student:
                check('teacher_answer_count',page.locator('.book-body .answer').count()==len(questions))
                shared_regression(page,build,check)
                markers(page)
                for mode in ['questions','answers']:
                    pdfs.append(print_pdf(page,out,mode,len(questions),check,warnings))
            else:
                check('student_no_private_dom_or_print_options',page.locator('.answer,.teacher-only,.question-analysis,[name="print-mode"][value="answers"],#print-notes,#print-sources').count()==0)
            page.set_viewport_size({'width':390,'height':844})
            check(label+'_mobile_no_horizontal_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            page.evaluate('scrollTo({top:0,behavior:"instant"})')
            page.screenshot(path=str(out/'verification'/f'{label}-mobile.png'))
            page.locator('#print-open').click()
            check(label+'_mobile_print_dialog_reachable',page.locator('#print-submit').evaluate('(el)=>{const a=el.getBoundingClientRect(),b=el.closest("dialog").getBoundingClientRect();return a.top>=b.top&&a.bottom<=b.bottom&&b.left>=0&&b.right<=innerWidth}'))
            page.keyboard.press('Escape')
            page.set_viewport_size({'width':1440,'height':1000})
        with tempfile.TemporaryDirectory(prefix='hujiao-student-') as temp:
            with zipfile.ZipFile(out/'student.zip') as archive:
                archive.extractall(temp)
            ready(page,Path(temp)/'student.html')
            check('student_zip_independent_offline_render',not page.evaluate('window.__mathErrors') and rendered_source_formula_count(page)==formula_count(blocks,True) and page.evaluate('[...document.images].every(i=>i.complete&&i.naturalWidth>0)') and page.locator('.question').count()==len(questions))
        check('javascript_no_exceptions',not javascript_errors,javascript_errors)
    except Exception as error:
        errors.append({'name':'validation_exception','error':str(error)})
        (out/'verification/error.log').write_text(traceback.format_exc(), encoding='utf-8')
    finally:
        page.close()
    report['status']='failed' if errors else 'passed'
    report['counts']={'questions':len([b for b in blocks if b['type']=='question']),'answers':build['answers'],'teacher_formulas':formula_count(blocks),'student_formulas':formula_count(blocks,True),'checks':len(checks),'errors':len(errors),'warnings':len(warnings)}
    save_json(target,report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--section',type=Path)
    source.add_argument('--catalog',type=Path)
    parser.add_argument('--book')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    paths=[args.section] if args.section else section_paths(args.catalog,args.book)
    failed=0
    with sync_playwright() as pw:
        browser=launch_browser(pw, headless=True)
        for path in paths:
            try:
                report=validate_section(path,browser,args.force)
                failed+=report['status']!='passed'
                print(json.dumps({k:report.get(k) for k in ['id','status','counts','cached']},ensure_ascii=False),flush=True)
            except Exception as error:
                failed+=1
                print(json.dumps({'section_json':str(path),'status':'failed','error':str(error)},ensure_ascii=False),flush=True)
        browser.close()
    return bool(failed)


if __name__=='__main__':
    raise SystemExit(main())
