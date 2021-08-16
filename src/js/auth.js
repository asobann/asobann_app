import Amplify, {Auth, Hub} from 'aws-amplify';
import {baseUrl} from "./util";

const asobannConfig = {};

async function loadAsobannConfig() {
    const url = baseUrl() + "config";
    const response = await fetch(url);
    const data = await response.json();
    Object.assign(asobannConfig, data);
    return asobannConfig;
}

function doNothing() {
}

function configureCognito(asobannConfig) {
    Amplify.configure({
        Auth: {

            // REQUIRED only for Federated Authentication - Amazon Cognito Identity Pool ID
            // identityPoolId: 'XX-XXXX-X:XXXXXXXX-XXXX-1234-abcd-1234567890ab',

            // REQUIRED - Amazon Cognito Region
            region: asobannConfig.aws.region,

            // OPTIONAL - Amazon Cognito Federated Identity Pool Region
            // Required only if it's different from Amazon Cognito Region
            // identityPoolRegion: 'XX-XXXX-X',

            // OPTIONAL - Amazon Cognito User Pool ID
            userPoolId: asobannConfig.aws.cognito.userPoolId,

            // OPTIONAL - Amazon Cognito Web Client ID (26-char alphanumeric string)
            userPoolWebClientId: asobannConfig.aws.cognito.clientId,

            // OPTIONAL - Enforce user authentication prior to accessing AWS resources or not
            // mandatorySignIn: false,

            // OPTIONAL - Configuration for cookie storage
            // Note: if the secure flag is set to true, then the cookie transmission requires a secure protocol
            // cookieStorage: {
            //     // REQUIRED - Cookie domain (only required if cookieStorage is provided)
            //     domain: '.yourdomain.com',
            //     // OPTIONAL - Cookie path
            //     path: '/',
            //     // OPTIONAL - Cookie expiration in days
            //     expires: 365,
            //     // OPTIONAL - See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite
            //     sameSite: "strict" | "lax",
            //     // OPTIONAL - Cookie secure flag
            //     // Either true or false, indicating if the cookie transmission requires a secure protocol (https).
            //     secure: true
            // },

            // OPTIONAL - customized storage object
            // storage: MyStorage,

            // OPTIONAL - Manually set the authentication flow type. Default is 'USER_SRP_AUTH'
            // authenticationFlowType: 'USER_PASSWORD_AUTH',

            // OPTIONAL - Manually set key value pairs that can be passed to Cognito Lambda Triggers
            // clientMetadata: { myCustomKey: 'myCustomValue' },

            // OPTIONAL - Hosted UI configuration
            oauth: {
                domain: asobannConfig.aws.cognito.oauth.domain,
                scope: ['phone', 'email', 'profile', 'openid', 'aws.cognito.signin.user.admin'],
                redirectSignIn: asobannConfig.aws.cognito.oauth.redirectSignIn,
                redirectSignOut: asobannConfig.aws.cognito.oauth.redirectSignOut,
                responseType: 'code' // or 'token', note that REFRESH token will only be generated when the responseType is code
            }
        }
    });

    // You can get the current config object
    const currentConfig = Auth.configure();
    return currentConfig;
}

async function config() {
    await loadAsobannConfig();
    auth.cognitoConfig = configureCognito(asobannConfig);
}

config().then(() => auth.updateAuthenticationStatus());

const auth = {
    federatedSignIn: function (opts) {
        Auth.federatedSignIn(opts).then(doNothing);
    },

    signOut: function () {
        Auth.signOut().then(doNothing);
    },

    updateAuthenticationStatus: function () {
        Auth.currentAuthenticatedUser()
            .then(r => {
                auth.userInfo = r;
                console.log('getUser', auth.userInfo);
            }).catch(e => console.error(e));
    },
};

export {Amplify, Hub, auth};