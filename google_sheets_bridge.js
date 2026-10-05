/**
 * ==============================================================================
 * GospelFlow 专属 Google 表格云端双向桥接脚本 (完美适配【安桑每日爆贴】)
 * ==============================================================================
 */

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('✝️ 恩典文案工具助手')
    .addItem('一键检查当前表格工作表', 'checkAllSheets')
    .addToUi();
}

function checkAllSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const names = ss.getSheets().map(s => s.getName()).join('、');
  SpreadsheetApp.getUi().alert('📋 当前表格包含的工作表有：\n' + names);
}

/**
 * Webhook GET 接口：智能读取【安桑每日爆贴】或【拆分文案】
 */
function doGet(e) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheetParam = (e && e.parameter && e.parameter.sheet) ? e.parameter.sheet.trim() : '';
    const reqType = (e && e.parameter && e.parameter.type) ? e.parameter.type : '';

    let s = null;
    if (sheetParam) {
      s = ss.getSheetByName(sheetParam);
    }

    // 智能兜底查找常用表名
    if (!s) {
      s = ss.getSheetByName('安桑每日爆贴') || 
          ss.getSheetByName('爆贴文案库') || 
          ss.getSheetByName('拆分文案') || 
          ss.getSheets()[0];
    }

    const lastRow = s.getLastRow();
    if (lastRow < 2) {
      return createJsonResponse({
        status: 'success',
        sheetName: s.getName(),
        rawList: [],
        data: { hooks: [], pains: [], values: [], ctas: [] },
        message: '工作表行数不足'
      });
    }

    const lastCol = Math.max(s.getLastColumn(), 4);
    const allValues = s.getRange(2, 1, lastRow - 1, lastCol).getValues();

    // 1. 如果是请求原始整篇爆款（或默认读取【安桑每日爆贴】）
    if (reqType === 'raw' || s.getName().includes('爆贴') || s.getName().includes('原文')) {
      const rawList = [];
      allValues.forEach((row, idx) => {
        // B 列是中文 (index 1), C 列是葡语 (index 2), D 列是播放量 (index 3)
        const chinese = row[1] ? String(row[1]).trim() : '';
        const portuguese = row[2] ? String(row[2]).trim() : '';
        const views = row[3] ? String(row[3]).trim() : '';
        
        // 自动忽略第 2、3 行的空单元格
        if (chinese) {
          rawList.push({
            rowId: idx + 2,
            chinese: chinese,
            portuguese: portuguese,
            views: views
          });
        }
      });

      return createJsonResponse({
        status: 'success',
        sheetName: s.getName(),
        rawList: rawList,
        total: rawList.length
      });
    }

    // 2. 如果是读取已经拆好的 4 列素材表
    const hooks = [];
    const pains = [];
    const values = [];
    const ctas = [];

    allValues.forEach(row => {
      // B~E 列对应 4 段
      if (row[1] && String(row[1]).trim()) hooks.push(String(row[1]).trim());
      if (row[2] && String(row[2]).trim()) pains.push(String(row[2]).trim());
      if (row[3] && String(row[3]).trim()) values.push(String(row[3]).trim());
      if (row[4] && String(row[4]).trim()) ctas.push(String(row[4]).trim());
    });

    return createJsonResponse({
      status: 'success',
      sheetName: s.getName(),
      data: { hooks, pains, values, ctas },
      stats: { totalHooks: hooks.length }
    });

  } catch (error) {
    return createJsonResponse({ status: 'error', message: '读取表格异常: ' + error.toString() });
  }
}

/**
 * Webhook POST 接口：写入【成品】表
 */
function doPost(e) {
  try {
    const req = JSON.parse(e.postData.contents);
    const rows = req.rows;
    const targetSheetName = req.targetSheet || '成品';
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let t = ss.getSheetByName(targetSheetName) || ss.insertSheet(targetSheetName);
    
    // 如果是新表，写表头
    if (t.getLastRow() < 1) {
      t.getRange(1, 1, 1, 3).setValues([['序号 (ID)', '中文完整短视频脚本', '非洲葡萄牙语译文']]).setBackground('#e6f4ea').setFontWeight('bold');
    }

    const lastRow = t.getLastRow();
    if (lastRow > 1) {
      t.getRange(2, 1, lastRow - 1, 3).clearContent();
    }
    t.getRange(2, 1, rows.length, 3).setValues(rows);

    return createJsonResponse({
      status: 'success',
      message: '已成功写入 ' + rows.length + ' 条成品文案到【' + t.getName() + '】！'
    });
  } catch (error) {
    return createJsonResponse({ status: 'error', message: '回写异常: ' + error.toString() });
  }
}

function createJsonResponse(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}
