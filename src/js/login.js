import {Amplify, Hub, auth} from "./auth.js"
import {baseUrl} from "./util";

Hub.listen("auth", ({ payload: { event, data } }) => {
    switch (event) {
        case "signIn":
            break;
        case "customOAuthState":
            const params = JSON.parse(data);
            window.location = baseUrl() + params.redirectUri;
            break;
    }
});


