async (page) => {
  const root = 'outputs/教材可视化编排小样';
  const check = (ok, message) => { if (!ok) throw Error(message); };
  const state = () => page.evaluate(() => bookComposer.getLayout());
  const ready = () => page.waitForFunction(() => [...document.querySelectorAll('.interactive-block .frame-status')].every(s => s.hidden));
  await page.setViewportSize({width: 1440, height: 1000});
  await page.evaluate(() => localStorage.removeItem('hujiao-visual-layout-prototype-v1'));
  await page.reload(); await ready();

  await page.frameLocator('.interactive-block iframe').getByRole('button', {name: '更扁的椭圆', exact: true}).click();
  await page.waitForFunction(() => bookComposer.getLayout().placements[0].state.c === 4.5);
  await page.locator('[data-asset="ellipse"] [data-action="preview"]').click();
  await page.frameLocator('#preview-content iframe').getByRole('button', {name: '两焦点重合', exact: true}).click();
  check((await state()).placements[0].state.c === 4.5, '预览污染正文参数');
  await page.locator('#preview-close').click();

  await page.locator('[data-anchor="ellipse-equation"]').click();
  await page.locator('[data-asset="ellipse"] [data-action="insert"]').click();
  await page.waitForFunction(() => bookComposer.getLayout().placements.length === 2); await ready();
  const two = (await state()).placements;
  check(two[0].state.c === 4.5 && two[1].state.c === 3 && two[1].afterBlockId === 'ellipse-equation', '插入位置或独立参数错误');
  await page.locator('#undo').click();
  await page.waitForFunction(() => bookComposer.getLayout().placements.length === 1); await ready();
  check((await state()).placements[0].state.c === 4.5, '撤销没有保留原实例参数');

  await page.locator('[data-section="x1-3-4"]').click();
  await page.waitForFunction(() => bookComposer.getLayout().currentSection === 'x1-3-4');
  await page.locator('[data-asset="perpendicular"]').dragTo(page.locator('[data-anchor="space-directions"]'));
  await page.waitForFunction(() => bookComposer.getLayout().placements.length === 2); await ready();
  await page.frameLocator('.interactive-block iframe').locator('#mode').selectOption('parallel');
  await page.waitForFunction(() => bookComposer.getLayout().placements.find(p => p.assetId === 'perpendicular').state.mode === 'parallel');
  await page.screenshot({path: root + '/desktop-space.png'});

  const beforeExport = await state();
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#export').click();
  await (await downloadPromise).saveAs(root + '/qa-roundtrip.json');
  await page.locator('.interactive-block [data-action="remove"]').click();
  await page.waitForFunction(() => bookComposer.getLayout().placements.length === 1);
  await page.locator('#import-file').setInputFiles(root + '/qa-roundtrip.json');
  await page.waitForFunction(() => bookComposer.getLayout().placements.length === 2); await ready();
  check(JSON.stringify((await state()).placements) === JSON.stringify(beforeExport.placements), '导入导出参数未完整恢复');
  await page.locator('#read-mode').click();
  check(await page.locator('.library').isHidden() && await page.locator('.drop-zone').first().isHidden(), '阅读模式未隐藏编排控件');
  await page.locator('#edit-mode').click();

  // Simulate an unresponsive module; navigation must stop, removal must remain recoverable.
  await page.locator('.interactive-block iframe').evaluate(el => { el.srcdoc = '<!doctype html><p>模拟无响应模块</p>'; });
  await page.locator('[data-section="x1-2-2"]').click();
  await page.waitForFunction(() => document.querySelector('#toast').textContent.includes('仍停留'));
  check((await state()).currentSection === 'x1-3-4', '状态超时仍切换章节');
  check(await page.locator('#section-select').inputValue() === 'x1-3-4', '切章失败后下拉框失配');
  page.once('dialog', dialog => dialog.accept());
  await page.locator('.interactive-block [data-action="remove"]').click();
  await page.waitForFunction(() => bookComposer.getLayout().placements.length === 1);

  await page.evaluate(() => localStorage.removeItem('hujiao-visual-layout-prototype-v1'));
  await page.reload(); await ready();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({path: root + '/desktop.png'});
  await page.setViewportSize({width: 390, height: 844});
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '手机正文横向溢出');
  await page.locator('#library-toggle').click();
  check(await page.locator('.library').isVisible(), '手机资源抽屉打不开');
  await page.waitForFunction(() => document.querySelector('.library').getBoundingClientRect().right <= innerWidth + 0.1);
  await page.screenshot({path: root + '/mobile.png'});
  await page.locator('#library-close').click();
  await page.setViewportSize({width: 1440, height: 1000});
}
