const JSDOMEnvironment = require('jest-environment-jsdom').default;

// jest-environment-jsdomはNode.js組み込みのfetchを引き継がない。dev_inspector.jsが
// モジュールロード時に即座にfetch()を呼ぶため、テスト実行時にjsdom側のglobalへ
// Node.js側のfetchをコピーする(本番はブラウザなので実物のfetchがある)。
class JSDOMEnvironmentWithFetch extends JSDOMEnvironment {
    async setup() {
        await super.setup();
        if (typeof this.global.fetch === 'undefined') {
            this.global.fetch = fetch;
            this.global.Headers = Headers;
            this.global.Request = Request;
            this.global.Response = Response;
        }
    }
}

module.exports = JSDOMEnvironmentWithFetch;
