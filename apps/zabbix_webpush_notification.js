var Djing2 = {
    token: null,
    message: null,
    domain: null,
    dev_ip: null,
    status: null,

    sendMessage: function() {
        const params = {
            dev_ip: Djing2.dev_ip,
            status: Djing2.status,
            message: Djing2.message
        }
        request = new CurlHttpRequest(),
        url = Djing2.domain + '/api/devices/all/zbx_monitoring_event/';

        if (Djing2.token !== null) {
            request.AddHeader('authorization: Token ' + Djing2.token);
        }

        request.AddHeader('Content-Type: application/json');

        const data = JSON.stringify(params);

        // Remove replace() function if you want to see the exposed token in the log file.
        Zabbix.Log(4, '[Djing2 Webhook] URL: ' + url);
        Zabbix.Log(4, '[Djing2 Webhook] data: ' + data);
        var response = request.Post(url, data);
        Zabbix.Log(4, '[Djing2 Webhook] HTTP code: ' + request.Status());

        response = JSON.parse(response);

        if (request.Status() !== 200) {
            Zabbix.Log(4, '[Djing2 Webhook] HTTP response: ' + JSON.stringify(request));
            if (typeof response.text === 'string') {
                throw response.text;
            }
            else {
                throw 'Unknown error. Check debug log for more information.'
            }
        }
    }
}

try {
    var params = JSON.parse(value);

    if (typeof params.Token === 'undefined') {
        throw 'Incorrect value is given for parameter "Token": parameter is missing';
    } else {
        Djing2.token = params.Token;
    }

    if (params.Domain) {
        Djing2.domain = params.Domain
    } else {
        throw 'Empty value in "domain" parameter';
    }

    Djing2.message = params.Message;

    Djing2.dev_ip = params.DevIp
    Djing2.status = params.Status

    Djing2.sendMessage();

    return 'OK';
}
catch (error) {
    Zabbix.Log(4, '[Djing2 Webhook] notification failed: ' + error);
    throw 'Sending failed: ' + error + '.';
}
