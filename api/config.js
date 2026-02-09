// Vercel Serverless Function - 設定を返すAPI
export default function handler(req, res) {
    // CORSヘッダー
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');

    // 環境変数から設定を取得
    const config = {
        password: process.env.APP_PASSWORD,
        jsonbinApiKey: process.env.JSONBIN_API_KEY,
        raceDataBinId: process.env.RACE_DATA_BIN_ID,
        gasUrl: process.env.GAS_URL
    };

    res.status(200).json(config);
}
