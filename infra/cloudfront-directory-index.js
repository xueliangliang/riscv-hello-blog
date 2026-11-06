function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // Redirect before rewriting directories, so public URLs never expose index.html.
  var host = request.headers && request.headers.host;
  if (host && host.value.toLowerCase() === 'xueliangliang.dev') {
    var parameters = [];
    var query = request.querystring || {};
    // CloudFront may enumerate keys differently from Node; sort names, not values.
    var keys = Object.keys(query).sort();
    for (var k = 0; k < keys.length; k++) {
      var key = keys[k];
      var values = query[key].multiValue || [query[key]];
      for (var i = 0; i < values.length; i++) {
        // CloudFront supplies URL-encoded query components; do not encode twice.
        parameters.push(key + '=' + values[i].value);
      }
    }
    var suffix = parameters.length ? '?' + parameters.join('&') : '';
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: {
        location: { value: 'https://blog.xueliangliang.dev' + uri + suffix },
        'cache-control': { value: 'public, max-age=300' }
      }
    };
  }

  if (uri.endsWith('/')) {
    request.uri += 'index.html';
  } else if (!uri.includes('.')) {
    request.uri += '/index.html';
  }

  return request;
}
