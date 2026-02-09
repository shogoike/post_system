/**
 * Google Apps Script (GAS) コード
 *
 * 設定手順:
 * 1. Google Sheets を新規作成
 * 2. メニュー「拡張機能」→「Apps Script」をクリック
 * 3. このコードを貼り付け
 * 4. SPREADSHEET_ID を実際のスプレッドシートIDに変更
 * 5. 「デプロイ」→「新しいデプロイ」
 * 6. 種類: 「ウェブアプリ」を選択
 * 7. アクセスできるユーザー: 「全員」に設定
 * 8. デプロイして生成されたURLをHTMLに入力
 */

// スプレッドシートのIDを設定（URLの /d/ と /edit の間の部分）
const SPREADSHEET_ID = '1cH2SFD6KhvFATF1Dwnw6zlq7fPTqkXD78UsbgmWub9E';

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    const pattern = data.pattern || '';
    const text = data.text || '';
    const timestamp = data.timestamp || new Date().toLocaleString('ja-JP');

    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = ss.getSheetByName('post') || ss.insertSheet('post');

    // 1列目: パターン名, 2列目: テキスト, 3列目: タイムスタンプ
    sheet.appendRow([pattern, text, timestamp]);

    return ContentService
      .createTextOutput(JSON.stringify({ success: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: error.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput('POST method required')
    .setMimeType(ContentService.MimeType.TEXT);
}
